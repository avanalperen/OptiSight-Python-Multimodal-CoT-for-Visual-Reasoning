import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import torch
from PIL import Image
import io
import logging
import os
import psutil
import gc
import time
import webbrowser
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model Path
# Model Path
# Use environment variable or fallback to local path (for development machine)
DEFAULT_MODEL_PATH = "/home/aavan/Desktop/Project Files/Vision Language Models/qwen2-vl-2b"
MODEL_PATH = os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)

# Global model and processor
model = None
processor = None

def get_ram_usage():
    return psutil.virtual_memory().percent

def get_gpu_info():
    """Returns GPU usage percentage and memory if available."""
    gpu_stats = {"percent": 0, "usage": "N/A"}
    if torch.cuda.is_available():
        try:
            import subprocess
            result = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,nounits,noheader"],
                encoding="utf-8"
            ).strip().split(',')
            gpu_stats["percent"] = int(result[0])
            gpu_stats["usage"] = f"{result[1].strip()}/{result[2].strip()} MB"
        except Exception:
            # Fallback to torch memory
            mem = torch.cuda.memory_reserved(0) / 1024 / 1024
            gpu_stats["usage"] = f"{mem:.0f} MB (Reserved)"
    return gpu_stats

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only RAM usage log at startup, no model loading
    logger.info(f"RAM Usage at Startup: {get_ram_usage()}%")
    
    # Open Browser
    try:
        logger.info("Opening dashboard...")
        try:
            browser = webbrowser.get('firefox')
            browser.open_new_tab("http://localhost:8000")
        except:
            webbrowser.open_new_tab("http://localhost:8000")
    except Exception as e:
        logger.warning(f"Could not open browser automatically: {e}")
        
    yield
    # Explicitly clear model on exit to free memory
    global model
    if model is not None:
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

app = FastAPI(lifespan=lifespan)

# Setup Templates
templates = Jinja2Templates(directory="templates")

# Ensure prompts and results directories exist
os.makedirs("prompts", exist_ok=True)
os.makedirs("results", exist_ok=True)

# Custom Log Filter to silence /stats
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/stats" not in record.getMessage()

# Apply filter to uvicorn access logs
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return HTMLResponse(content="", status_code=204)

@app.get("/stats")
async def get_stats():
    return {
        "ram": get_ram_usage(),
        "gpu": get_gpu_info()
    }

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/save_prompt")
async def save_prompt(name: str = Form(...), content: str = Form(...)):
    try:
        # Sanitize filename
        safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
        if not safe_name:
            return {"status": "error", "message": "Invalid filename"}
        
        filepath = os.path.join("prompts", f"{safe_name}.txt")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"--- SAVED AT: {timestamp} ---\n\n")
            f.write(content)
        return {"status": "success", "message": f"Saved to prompts/{safe_name}.txt"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/save_result")
async def save_result(
    name: str = Form(...),
    prompt: str = Form(...),
    content: str = Form(...),
    metadata: str = Form(...),
    debug_log: str = Form(""),
    source_type: str = Form("unknown"),
    source_name: str = Form("Unknown")
):
    try:
        timestamp_full = time.strftime("%d-%m-%Y %H:%M:%S")
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip()
        filename = f"{safe_name}.txt"
        filepath = os.path.join("results", filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"=== ANALYSIS RESULT ===\n")
            f.write(f"Date/Time: {timestamp_full}\n\n")
            
            f.write(f"--- SOURCE ---\n")
            f.write(f"Type: {source_type}\n")
            f.write(f"File: {source_name}\n\n")
            
            f.write(f"--- PROMPT ---\n{prompt}\n\n")
            
            f.write(f"--- RESULT ---\n{content}\n\n")
            
            f.write(f"--- METADATA ---\n{metadata}\n\n")
            
            if debug_log:
                f.write(f"--- DEBUG LOG ---\n{debug_log}\n")
            
        return {"status": "success", "message": f"Saved to results/{filename}"}
    except Exception as e:
        logger.error(f"Error saving result: {e}")
        return {"status": "error", "message": str(e)}

def load_model_on_demand(device_choice="cpu"):
    global model, processor
    
    # If already loaded on the correct device, skip
    if model is not None:
        current_device = "cuda" if model.device.type == "cuda" else "cpu"
        if current_device == device_choice:
            return 0
    
    # Cleanup previous model if exists
    if model is not None:
        del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    start_load = time.time()
    logger.info(f"Loading model on {device_choice}...")
    
    try:
        if device_choice == "cuda":
            model = Qwen2VLForConditionalGeneration.from_pretrained(
                MODEL_PATH,
                torch_dtype=torch.float16,
                device_map="auto"
            )
        else:
            model = Qwen2VLForConditionalGeneration.from_pretrained(
                MODEL_PATH,
                torch_dtype=torch.float32,
                device_map="cpu",
                low_cpu_mem_usage=True
            )
        
        processor = AutoProcessor.from_pretrained(
            MODEL_PATH, 
            min_pixels=256*28*28, 
            max_pixels=512*28*28
        )
        load_time = time.time() - start_load
        logger.info(f"Model loaded on {device_choice} in {load_time:.2f}s")
        return load_time
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        model = None
        processor = None
        raise e

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    device_choice: str = Form("cpu")
):
    global model, processor
    
    import gc
    import time
    start_time = time.time()
    
    try:
        # On-demand loading
        load_time = load_model_on_demand(device_choice)
        
        ram_start = get_ram_usage()
        gpu_start = get_gpu_info()
        logger.info(f"--- Analysis Started ---")
        logger.info(f"Device Choice: {device_choice} (Load Time: {load_time:.2f}s)")
        logger.info(f"Prompt: {prompt}")
        
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Prepare conversation
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        
        # Preprocess
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
            ).to(model.device)

        # Inference with no_grad for memory efficiency
        inference_start = time.time()
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=128)
        inference_end = time.time()
            
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        
        total_time = time.time() - start_time
        inference_time = inference_end - inference_start
        
        ram_end = get_ram_usage()
        gpu_end = get_gpu_info()
        logger.info(f"Analysis Complete. Total time: {total_time:.2f}s")
        logger.info(f"Resources [End] - RAM: {ram_end}%, GPU: {gpu_end['percent']}% ({gpu_end['usage']})")
        
        # Cleanup small objects
        del inputs, generated_ids, generated_ids_trimmed
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return {
            "response": output_text[0],
            "debug": {
                "total_time": f"{total_time:.2f}s",
                "inference_time": f"{inference_time:.2f}s",
                "load_time": f"{load_time:.2f}s",
                "ram_usage": f"{ram_start}% -> {ram_end}%",
                "gpu_usage": f"{gpu_start['percent']}% ({gpu_start['usage']}) -> {gpu_end['percent']}% ({gpu_end['usage']})",
                "device": "GPU" if model.device.type == "cuda" else "CPU"
            }
        }

    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        return {"response": f"Error: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
