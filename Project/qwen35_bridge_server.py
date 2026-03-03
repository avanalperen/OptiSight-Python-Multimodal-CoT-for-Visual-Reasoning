from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM
from qwen_vl_utils import process_vision_info
import os
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("qwen35_bridge")

app = FastAPI()

class InferenceRequest(BaseModel):
    model_path: str
    image_path: str
    prompt: str
    device: str = "cuda"

# Global model/processor to keep them in VRAM
model = None
processor = None
current_model_path = None

def load_qwen35(model_path, device="cuda"):
    global model, processor, current_model_path
    if model is not None and current_model_path == model_path:
        return
    
    logger.info(f"Loading Qwen 3.5 from {model_path} on {device}...")
    target_device = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if target_device == "cuda" else torch.float32
    
    try:
        from transformers import Qwen3_5ForConditionalGeneration
        model_class = Qwen3_5ForConditionalGeneration
    except ImportError:
        logger.warning("Could not import Qwen3_5ForConditionalGeneration directly, falling back to AutoModelForCausalLM")
        model_class = AutoModelForCausalLM

    model = model_class.from_pretrained(
        model_path,
        torch_dtype=torch_dtype,
        device_map=target_device,
        trust_remote_code=True,
        attn_implementation="sdpa" if target_device == "cuda" else "eager",
        low_cpu_mem_usage=True
    )
    processor = AutoProcessor.from_pretrained(
        model_path,
        trust_remote_code=True,
        min_pixels=16*28*28,
        max_pixels=128*28*28
    )
    current_model_path = model_path
    logger.info("Model loaded successfully with SDPA and optimized pixel limits.")

@app.post("/analyze")
async def analyze(req: InferenceRequest):
    try:
        load_qwen35(req.model_path, req.device)
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": req.image_path},
                    {"type": "text", "text": f"Answer concisely. {req.prompt}"},
                ],
            }
        ]
        
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(model.device)
        
        with torch.no_grad():
            generated_ids = model.generate(
                **inputs, 
                max_new_tokens=150,
                do_sample=True,
                temperature=0.1,
                top_p=0.9,
                repetition_penalty=1.1
            )
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )
        
        return {"status": "success", "response": output_text[0]}
    except Exception as e:
        import traceback
        logger.error(f"Inference error: {str(e)}")
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
