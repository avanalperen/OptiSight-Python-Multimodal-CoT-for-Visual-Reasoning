from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from PIL import Image
try:
    from transformers import AutoProcessor, AutoModelForCausalLM, AutoModelForVision2Seq, AutoModelForMultimodalLM, AutoModelForImageTextToText, Sam2Processor, Sam2Model
except ImportError:
    from transformers import AutoProcessor, AutoModelForCausalLM, Sam2Processor, Sam2Model
    try:
        from transformers import AutoModelForMultimodalLM
    except ImportError:
        AutoModelForMultimodalLM = None
    try:
        from transformers import AutoModelForImageTextToText
    except ImportError:
        AutoModelForImageTextToText = None
    AutoModelForVision2Seq = None
from qwen_vl_utils import process_vision_info
import os
import uvicorn
import logging
import config
import time

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
sam_model = None
sam_processor = None
current_model_path = None

def load_sam2(device="cuda"):
    global sam_model, sam_processor
    if sam_model is not None:
        return 0, device
    
    start_load = time.time()
    logger.info(f"Pre-loading SAM 2.1 (Tiny) on {device} in Bridge Process...")
    
    try:
        sam_processor = Sam2Processor.from_pretrained(config.SAM2_PATH)
        target_device = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if target_device == "cuda" else torch.float32
        
        sam_model = Sam2Model.from_pretrained(
            config.SAM2_PATH,
            torch_dtype=torch_dtype,
            device_map=target_device
        )
        load_time = time.time() - start_load
        logger.info(f"SAM 2.1 pre-loaded successfully in bridge process in {load_time:.2f}s (Status: IDLE)")
        return load_time, target_device
    except Exception as e:
        logger.error(f"Failed to pre-load SAM 2.1 in bridge: {e}")
        sam_model = None
        sam_processor = None
        return 0, "cpu"

class LoadRequest(BaseModel):
    model_path: str
    device: str = "cuda"
    current_mode: str = "habitat"

def load_qwen35(model_path, device="cuda", current_mode="habitat"):
    global model, processor, current_model_path
    
    # Normalize path for WSL/Linux compatibility
    model_path = os.path.abspath(model_path)
    
    vlm_load_time = 0
    target_device = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"
    
    if model is not None and current_model_path == model_path:
        vlm_load_time = 0
    else:
        start_vlm = time.time()
        logger.info(f"Loading Qwen 3.5 from local path: {model_path} on {device}...")
        torch_dtype = torch.float16 if target_device == "cuda" else torch.float32
        
        try:
            # Try different Auto classes based on transformers version availability
            if AutoModelForMultimodalLM is not None:
                logger.info("Loading via AutoModelForMultimodalLM...")
                model = AutoModelForMultimodalLM.from_pretrained(
                    model_path,
                    torch_dtype=torch_dtype,
                    device_map=target_device,
                    trust_remote_code=True,
                    attn_implementation="sdpa" if target_device == "cuda" else "eager",
                    low_cpu_mem_usage=True
                )
            elif AutoModelForVision2Seq is not None:
                logger.info("Loading via AutoModelForVision2Seq...")
                model = AutoModelForVision2Seq.from_pretrained(
                    model_path,
                    torch_dtype=torch_dtype,
                    device_map=target_device,
                    trust_remote_code=True,
                    attn_implementation="sdpa" if target_device == "cuda" else "eager",
                    low_cpu_mem_usage=True
                )
            elif AutoModelForImageTextToText is not None:
                logger.info("Loading via AutoModelForImageTextToText...")
                model = AutoModelForImageTextToText.from_pretrained(
                    model_path,
                    torch_dtype=torch_dtype,
                    device_map=target_device,
                    trust_remote_code=True,
                    low_cpu_mem_usage=True
                )
            else:
                raise ImportError("No suitable AutoModel class found for Multimodal/Vision loading.")
                
        except Exception as e:
            logger.warning(f"Failed to load via Vision-specific classes: {e}. Falling back to AutoModelForCausalLM.")
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch_dtype,
                device_map=target_device,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
        
        # Optional: ensure kwarg validation is off just in case of remote code quirks
        if hasattr(model, "generation_config"):
            model.generation_config.validate_model_kwargs = False

        processor = AutoProcessor.from_pretrained(
            model_path,
            trust_remote_code=True,
            min_pixels=16*28*28,
            max_pixels=1024*28*28
        )
        current_model_path = model_path
        vlm_load_time = time.time() - start_vlm
        logger.info(f"Qwen 3.5 loaded successfully in {vlm_load_time:.2f}s.")
    
    # Pre-load SAM 2.1 simultaneously in the bridge process
    if current_mode == "habitat":
        sam_load_time, sam_device = load_sam2(device)
    else:
        sam_load_time, sam_device = 0.0, "N/A"
    
    return {
        "vlm_time": vlm_load_time,
        "vlm_device": target_device,
        "sam_time": sam_load_time,
        "sam_device": sam_device
    }

@app.post("/load")
async def load_endpoint(req: LoadRequest):
    try:
        info = load_qwen35(req.model_path, req.device, req.current_mode)
        return {"status": "success", **info}
    except Exception as e:
        logger.error(f"Load error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/analyze")
async def analyze(req: InferenceRequest):
    try:
        load_qwen35(req.model_path, req.device, "habitat")
        
        # Context-aware prompt prefixing
        prefix = ""
        if "[VISION SYSTEM: ANGLE GRID]" in req.prompt:
            prefix = "Locate the goal using the green grid lines. Output ONLY the Observation, Reasoning, and Command. "
        elif "[VISION SYSTEM: BOUNDING BOX]" in req.prompt:
            # Flexible grounding-focused prefix
            prefix = "Detect the target goal in the image. You must provide its precise location using <box>(x1,y1),(x2,y2)</box> coordinates. "
        else:
            # Fallback for manual or general prompts
            prefix = "Analyze the image and follow the instructions carefully. "
            
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": req.image_path},
                    {"type": "text", "text": f"{prefix}{req.prompt}"},
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
        
        # Filter out mm_token_type_ids as it's known to cause "unused model_kwargs" errors 
        # with Qwen2-VL/3.5 models in certain transformers versions.
        inputs.pop("mm_token_type_ids", None)
        
        with torch.no_grad():
            generated_ids = model.generate(
                **inputs, 
                max_new_tokens=150,
                do_sample=True,
                temperature=0.1,
                top_p=0.9,
                repetition_penalty=1.2,
                use_cache=True
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
