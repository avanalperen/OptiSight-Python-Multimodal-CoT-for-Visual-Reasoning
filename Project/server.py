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
import webbrowser
try:
    from habitat_controller import HabitatController
    HABITAT_AVAILABLE = True
except ImportError:
    HabitatController = None
    HABITAT_AVAILABLE = False
    logger.warning("Habitat Sim not found or failed to load. Simulation features will be disabled.")

import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model Path
# Model Path
MODEL_PATH = config.MODEL_PATH

# Global model and processor
model = None
processor = None

def get_ram_usage():
    return psutil.virtual_memory().percent

# Global Habitat Controller
habitat_controller = None
# Global Habitat Controller
habitat_controller = None
import threading
habitat_lock = threading.Lock()
SCENE_PATH = config.SCENE_PATH

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
        try:
            model.to("cpu")
        except:
            pass
        del model
        model = None
    if processor is not None:
        del processor
        processor = None
        
    gc.collect()
    gc.collect() # Multiple passes
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        torch.cuda.synchronize()

    start_load = time.time()
    logger.info(f"Loading model on {device_choice}...")
    
    try:
        if device_choice == "cuda":
            model = Qwen2VLForConditionalGeneration.from_pretrained(
                MODEL_PATH,
                torch_dtype=torch.float16,
                device_map="auto",
                attn_implementation="sdpa"
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
            min_pixels=16*28*28, 
            max_pixels=128*28*28
        )
        load_time = time.time() - start_load
        logger.info(f"Model loaded on {device_choice} in {load_time:.2f}s")
        return load_time
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        model = None
        processor = None
        raise e

@app.post("/load_model")
async def load_model_endpoint(device_choice: str = Form("cuda")):
    try:
        load_time = load_model_on_demand(device_choice)
        return {"status": "success", "message": f"Model loaded on {device_choice} in {load_time:.2f}s"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/unload_model")
async def unload_model_endpoint():
    global model, processor
    if model is not None:
        try:
            model.to("cpu")
        except:
            pass
        del model
        model = None
    if processor is not None:
        del processor
        processor = None
        
    # Force Python GC first
    gc.collect()
    gc.collect()
    
    # Then force PyTorch CUDA Memory allocator release
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        torch.cuda.synchronize()
        
    logger.info("Model unloaded from memory. Cleanup complete.")
    return {"status": "success", "message": "Model unloaded from memory"}

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
            generated_ids = model.generate(**inputs, max_new_tokens=200, do_sample=False)
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

# --- Habitat Routes ---

@app.get("/list_scenes")
async def list_scenes():
    scene_dir = "/home/aavan/Desktop/Project Files/My Python Project/Project/test habitats"
    if not os.path.exists(scene_dir):
        return {"scenes": []}
    scenes = [f for f in os.listdir(scene_dir) if f.endswith('.glb') or f.endswith('.json')]
    return {"scenes": sorted(scenes)}

@app.post("/init_sim")
async def init_sim(file: UploadFile = File(None), scene_name: str = Form(None)):
    global habitat_controller
    if not HABITAT_AVAILABLE:
        return {"status": "error", "message": "Habitat Sim is not installed or supported on this system."}
    
    try:
        if file:
            # Save uploaded file to test habitats
            upload_dir = "/home/aavan/Desktop/Project Files/My Python Project/Project/test habitats"
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, file.filename)
            contents = await file.read()
            with open(filepath, "wb") as f:
                f.write(contents)
            scene_to_use = filepath
            logger.info(f"Using uploaded scene: {scene_to_use}")
        elif scene_name:
            scene_to_use = os.path.join("/home/aavan/Desktop/Project Files/My Python Project/Project/test habitats", scene_name)
            if not os.path.exists(scene_to_use):
                return {"status": "error", "message": f"Scene {scene_name} not found"}
            logger.info(f"Using selected scene: {scene_to_use}")
        else:
            scene_to_use = SCENE_PATH
            logger.info(f"Using default scene: {scene_to_use}")

        # Check if this is an HSSD scene (by filename pattern or known list)
        # HSSD files usually look like "102343992.glb" or "108736611_177263226.glb"
        # We need the handle (filename without extension) and the dataset config
        hssd_config_path = "/home/aavan/Desktop/Project Files/AIHabitat Project/Hssd Habitat Dataset/hssd/hssd-hab.scene_dataset_config.json"
        
        sim_settings = {}
        if "hssd" in scene_to_use or os.path.exists(hssd_config_path):
             # Try to match filename to an HSSD ID
             basename = os.path.basename(scene_to_use)
             scene_handle = os.path.splitext(basename)[0]
             
             # Heuristic: If filename is numeric/ID-like, treat as HSSD
             # This allows us to load the full scene with objects
             if len(scene_handle) > 5 and scene_handle[0].isdigit():
                 logger.info(f"Detected potential HSSD scene: {scene_handle}. Using Dataset Config.")
                 sim_settings["dataset_config"] = hssd_config_path
                 scene_to_use = scene_handle # Pass ID instead of path

        with habitat_lock:
            habitat_controller = HabitatController(scene_to_use, **sim_settings)
        return {"status": "success", "message": f"Simulator initialized with {os.path.basename(scene_to_use)}"}
    except Exception as e:
        logger.error(f"Failed to init simulator: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/get_view")
async def get_view():
    global habitat_controller
    
    with habitat_lock:
        if habitat_controller is None:
            return {"status": "error", "message": "Simulator not initialized"}
        
        try:
            frame_base64 = habitat_controller.get_frame_as_base64()
            return {"status": "success", "frame": frame_base64}
        except Exception as e:
            logger.error(f"View error: {e}")
            return {"status": "error", "message": str(e)}

@app.post("/move")

async def move_agent(command: str = Form(...)):
    global habitat_controller

    with habitat_lock:
        if habitat_controller is None:
            return {"status": "error", "message": "Simulator not initialized"}
        
        try:
            frame_base64 = habitat_controller.move_agent(command)
            return {"status": "success", "frame": frame_base64}
        except Exception as e:
            logger.error(f"Movement error: {e}")
            return {"status": "error", "message": str(e)}

@app.post("/get_map")
async def get_map():
    global habitat_controller
    with habitat_lock:
        if habitat_controller is None:
            return {"status": "error", "message": "Simulator not initialized"}
        
        try:
            map_base64, map_info = habitat_controller.get_topdown_map_base64()
            if map_base64:
                return {"status": "success", "map": map_base64, "info": map_info}
            else:
                return {"status": "error", "message": map_info} # map_info contains error string
        except Exception as e:
            logger.error(f"Map generation error: {e}")
            return {"status": "error", "message": str(e)}

@app.post("/set_pose")
async def set_pose(
    norm_x: float = Form(...), 
    norm_y: float = Form(...),
    map_width: int = Form(...),
    map_height: int = Form(...)
):
    global habitat_controller
    with habitat_lock:
        if habitat_controller is None:
            return {"status": "error", "message": "Simulator not initialized"}
        
        try:
            # We need to reconstruct map_info partially
            # Set Pose needs dimensions to scale
            partial_info = {"width": map_width, "height": map_height}
            
            success, result = habitat_controller.set_agent_start_pose(norm_x, norm_y, partial_info)
            if success:
                 return {"status": "success", "frame": result}
            else:
                 return {"status": "error", "message": result}
        except Exception as e:
            logger.error(f"Set pose error: {e}")
            return {"status": "error", "message": str(e)}

@app.post("/interact")
async def interact_agent():
    global habitat_controller

    with habitat_lock:
        if habitat_controller is None:
            return {"status": "error", "message": "Simulator not initialized"}
        
        try:
            # Call interact on the controller
            frame_base64 = habitat_controller.move_agent("interact")
            return {"status": "success", "frame": frame_base64, "message": "Interaction triggered"}
        except Exception as e:
            logger.error(f"Interaction error: {e}")
            return {"status": "error", "message": str(e)}

@app.post("/reset_camera")
async def reset_camera():
    global habitat_controller
    with habitat_lock:
        if habitat_controller is None:
            return {"status": "error", "message": "Simulator not initialized"}
        try:
            frame_base64 = habitat_controller.reset_camera()
            return {"status": "success", "frame": frame_base64}
        except Exception as e:
            return {"status": "error", "message": str(e)}

@app.post("/snap_to_floor")
async def snap_to_floor():
    global habitat_controller
    with habitat_lock:
        if habitat_controller is None:
            return {"status": "error", "message": "Simulator not initialized"}
        try:
            frame_base64 = habitat_controller.snap_to_floor()
            return {"status": "success", "frame": frame_base64}
        except Exception as e:
            return {"status": "error", "message": str(e)}

@app.post("/generate_video")
async def generate_video(
    points: str = Form(None), # JSON string of points list
    filename: str = Form("route_video.mp4")
):
    global habitat_controller
    if habitat_controller is None:
        return {"status": "error", "message": "Simulator not initialized"}
    
    try:
        # Parse points if provided
        parsed_points = None
        if points:
            import json
            try:
                # Expecting [[x,y,z], [x,y,z]]
                parsed_points = json.loads(points)
            except:
                pass
        
        filepath = os.path.join("static/test_videos", filename)
        success, result = habitat_controller.generate_route_video(parsed_points, filepath)
        
        if success:
            return {"status": "success", "video_url": f"/static/test_videos/{filename}"}
        else:
            return {"status": "error", "message": result}
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
