import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from autonomous_navigator import AutonomousNavigator
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
import json
import requests
import subprocess
try:
    from habitat_controller import HabitatController
    HABITAT_AVAILABLE = True
except ImportError:
    HabitatController = None
    HABITAT_AVAILABLE = False

from collections import deque
import re

from collections import deque
import re

logger = logging.getLogger(__name__)

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
bridge_process = None

def stop_bridge_server():
    global bridge_process
    if bridge_process:
        logger.info("Stopping Qwen 3.5 Bridge Server...")
        import signal
        try:
            os.killpg(os.getpgid(bridge_process.pid), signal.SIGTERM)
        except:
            pass
        bridge_process = None

def ensure_bridge_server():
    global bridge_process
    if bridge_process is None or bridge_process.poll() is not None:
        logger.info("Starting Qwen 3.5 Bridge Server on port 8001...")
        import subprocess
        bridge_process = subprocess.Popen(
            ["conda", "run", "-n", "qwen35", "python", "qwen35_bridge_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        # Wait for health
        for _ in range(30):
            try:
                resp = requests.get("http://127.0.0.1:8001/health", timeout=1)
                if resp.status_code == 200:
                    logger.info("Bridge server is healthy.")
                    return True
            except:
                pass
            time.sleep(1)
        logger.error("Bridge server failed to respond.")
        return False
    return True

def get_ram_usage():
    return psutil.virtual_memory().percent

# Global Habitat Controller
habitat_controller = None
# Global Habitat Controller
habitat_controller = None
import threading
habitat_lock = threading.Lock()
SCENE_PATH = config.SCENE_PATH
SETTINGS_FILE = "settings.json"
SCENARIOS_FILE = "scenarios.json"
SESSION_SETTINGS = {"height": 0.0, "height_lock": False}

def load_scenarios():
    if os.path.exists(SCENARIOS_FILE):
        try:
            with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading scenarios: {e}")
    
    # Default structure
    return {
        'scenario1': {
            'core': "",
            'searching': "",
            'navigating': "",
            'recovering': ""
        }
    }

def save_scenarios(scenarios):
    try:
        with open(SCENARIOS_FILE, "w", encoding="utf-8") as f:
            json.dump(scenarios, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving scenarios: {e}")
        return False

def load_settings():
    # For session-only settings, we return the current session settings
    # and do not load from a file.
    return SESSION_SETTINGS

def save_settings(settings):
    global SESSION_SETTINGS
    SESSION_SETTINGS.update(settings)

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
    stop_bridge_server()
    global model
    if model is not None:
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

app = FastAPI(lifespan=lifespan)

# Setup Templates
templates = Jinja2Templates(directory="templates")

# Ensure prompts and results directories exist
os.makedirs("core prompts", exist_ok=True)
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

@app.get("/get_scenarios")
async def get_scenarios_endpoint():
    return load_scenarios()

@app.post("/save_scenarios")
async def save_scenarios_endpoint(request: Request):
    try:
        data = await request.json()
        if save_scenarios(data):
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Failed to save file"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/save_prompt")
async def save_prompt(name: str = Form(...), content: str = Form(...)):
    try:
        # Sanitize filename
        safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
        if not safe_name:
            return {"status": "error", "message": "Invalid filename"}
        
        # Ensure target directory exists
        save_dir = "core prompts"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        filepath = os.path.join(save_dir, f"{safe_name}.txt")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"--- SAVED AT: {timestamp} ---\n\n")
            f.write(content)
        return {"status": "success", "message": f"Saved to {save_dir}/{safe_name}.txt"}
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

def load_model_on_demand(device_choice="cpu", model_choice="qwen2-2b"):
    global model, processor
    
    # If already loaded on the correct device and correct model, skip
    if model is not None:
        # Current device check that handles both torch.device and string
        current_device = "cuda" if (hasattr(model.device, 'type') and model.device.type == "cuda") or model.device == "cuda" else "cpu"
        # We need a way to track which model is loaded if we want to skip.
        # For simplicity, if we are switching models, we should reload.
        # Adding a simple check based on model type or config might be needed, 
        # but for now, let's track the loaded model type globally.
        # Re-check current device
        current_device = "cuda" if (hasattr(model.device, 'type') and model.device.type == "cuda") or model.device == "cuda" else "cpu"
        if getattr(model, "loaded_model_choice", None) == model_choice and current_device == device_choice:
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
        
    for _ in range(3):
        gc.collect()
        if torch.cuda.is_available():
            with habitat_lock:
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                torch.cuda.synchronize()

    start_load = time.time()
    logger.info(f"Loading {model_choice} on {device_choice}...")
    
    # Determine Model Path
    if model_choice == "qwen2-2b":
        target_model_path = config.QWEN_PATH
    elif model_choice == "qwen3.5-0.8b":
        target_model_path = config.QWEN35_08B_PATH
    elif model_choice == "qwen3.5-2b":
        target_model_path = config.QWEN35_2B_PATH
    else:
        target_model_path = config.QWEN_PATH # Fallback
    
    try:
        from transformers import AutoProcessor, AutoModelForCausalLM
        if model_choice == "qwen2-2b":
            if device_choice == "cuda":
                model = Qwen2VLForConditionalGeneration.from_pretrained(
                    target_model_path,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    attn_implementation="sdpa"
                )
            else:
                model = Qwen2VLForConditionalGeneration.from_pretrained(
                    target_model_path,
                    torch_dtype=torch.float32,
                    device_map="cpu",
                    low_cpu_mem_usage=True
                )
            processor = AutoProcessor.from_pretrained(
                target_model_path, 
                min_pixels=16*28*28, 
                max_pixels=128*28*28
            )
        elif model_choice in ["qwen3.5-0.8b", "qwen3.5-2b"]:
            # Ensure the bridge server is running
            ensure_bridge_server()
            # For Qwen 3.5, we don't load in this process (uses bridge script)
            model = type('MockModel', (), {'loaded_model_choice': model_choice, 'device': device_choice})()
            processor = None
            logger.info(f"{model_choice} managed via persistent bridge server.")
        
        model.loaded_model_choice = model_choice  # Track the loaded model
        
        load_time = time.time() - start_load
        logger.info(f"{model_choice} loaded on {device_choice} in {load_time:.2f}s")
        return load_time
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        model = None
        processor = None
        raise e

@app.post("/load_model")
async def load_model_endpoint(device_choice: str = Form("cuda"), model_choice: str = Form("qwen2-2b")):
    try:
        load_time = load_model_on_demand(device_choice, model_choice)
        return {"status": "success", "message": f"{model_choice} loaded on {device_choice} in {load_time:.2f}s"}
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
        
    # Force Python GC and CUDA cleanups multiple times
    import gc
    for _ in range(3):
        gc.collect()
        if torch.cuda.is_available():
            with habitat_lock:
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
    
    # Wait briefly for NVIDIA drivers to update their memory reporting
    import time
    time.sleep(1.0)
            
    logger.info("Model unloaded from memory. Cleanup complete.")
    return {"status": "success", "message": "Model unloaded from memory."}

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    device_choice: str = Form("cpu"),
    model_choice: str = Form("qwen2-2b"),
    habitat_submode: str = Form(None),
    memory_mode: str = Form("true")
):
    global model, processor, habitat_controller
    
    import gc
    import time
    start_time = time.time()
    
    try:
        # 1. Prompt Injection - Handle memory system
        if "{PREVIOUS_MEMORY}" in prompt and habitat_controller:
            if memory_mode.lower() == "true":
                mem_str = habitat_controller.get_memory_string()
                prompt = prompt.replace("{PREVIOUS_MEMORY}", mem_str)
                logger.info(f"Injected memory into prompt: {mem_str}")
            else:
                prompt = prompt.replace("Previous memory: {PREVIOUS_MEMORY}.", "")
                prompt = prompt.replace("{PREVIOUS_MEMORY}", "None")
                logger.info("Memory mode disabled, omitted memory from prompt.")
        
        # On-demand loading
        load_time = load_model_on_demand(device_choice, model_choice)
        
        ram_start = get_ram_usage()
        gpu_start = get_gpu_info()
        logger.info(f"--- Analysis Started ---")
        logger.info(f"Model Choice: {model_choice} | Device: {device_choice} (Load Time: {load_time:.2f}s)")
        logger.info(f"Prompt: {prompt}")
        
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # Aggressive Resize to improve performance (448px for Qwen)
        max_size = 448
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        inference_start = time.time()

        if model_choice == "qwen2-2b":
            # Qwen Preprocessing
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt},
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
                ).to(model.device)

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
                out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )
            final_response = output_text[0]
            del inputs, generated_ids, generated_ids_trimmed

        elif model_choice in ["qwen3.5-0.8b", "qwen3.5-2b"]:
            # Qwen 3.5 Inference via Bridge Server
            logger.info(f"Running {model_choice} inference via persistent bridge...")
            
            # 1. Save temp image
            temp_image_path = os.path.join(os.getcwd(), "temp_analyze_image.jpg")
            image.save(temp_image_path)
            
            # 2. Determine target path from config
            if model_choice == "qwen3.5-0.8b":
                target_path = config.QWEN35_08B_PATH
            else:
                target_path = config.QWEN35_2B_PATH
                
            # 3. Call Bridge Server API
            try:
                ensure_bridge_server() # Double check
                api_payload = {
                    "model_path": target_path,
                    "image_path": temp_image_path,
                    "prompt": prompt,
                    "device": device_choice
                }
                resp = requests.post("http://127.0.0.1:8001/analyze", json=api_payload, timeout=120)
                result_data = resp.json()
                
                if result_data.get("status") == "success":
                    final_response = result_data.get("response")
                else:
                    final_response = f"Bridge Error: {result_data.get('message')}"
                    logger.error(f"Bridge Inference Error: {result_data.get('message')}\nTraceback: {result_data.get('traceback')}")
            except Exception as e:
                final_response = f"Bridge Communication Error: {str(e)}"
                logger.error(f"Bridge Communication Error: {str(e)}")
            finally:
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)

        else:
            final_response = "Unsupported model selected."

        inference_end = time.time()
        
        # 2. Extract Reasoning/Command for Stateful Controller and Auto-Execution
        if habitat_submode in ['live', 'autonomous'] and habitat_controller:
            # Capture the memory state BEFORE we append the new action
            mem_str_for_display = habitat_controller.get_memory_string()
            
            # Sentence extraction for Reasoning
            reasoning_match = re.search(r'Reasoning:\s*(.*?)(?=\. <cmd>|$)', final_response, re.IGNORECASE)
            # If standard regex fails, look for 'Reasoning:' until the end or first period
            if not reasoning_match:
                reasoning_match = re.search(r'Reasoning:\s*(.*?)(?=\.|$)', final_response, re.IGNORECASE)
            
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "Reasoning omitted."
            
            # Command extraction: <cmd>...</cmd>
            command_match = re.search(r'<cmd>(.*?)</cmd>', final_response, re.IGNORECASE)
            
            if command_match:
                extracted_cmd = command_match.group(1).strip()
                logger.info(f"System identified command: {extracted_cmd} | Reasoning: {reasoning}")
                
                # Update persistent memory within the core controller
                habitat_controller.record_vlm_action(extracted_cmd, reasoning)
                
                # If autonomous, execute movement immediately in simulator
                if habitat_submode == 'autonomous':
                    with habitat_lock:
                        logger.info(f"AUTONOMOUS EXECUTION: {extracted_cmd}")
                        habitat_controller.move_agent(extracted_cmd)

        # 3. Clean and format the final response for display
        if habitat_submode in ['live', 'autonomous'] and habitat_controller:
            formatted_response = final_response
            
            # Add double newlines before keywords
            if memory_mode.lower() == "true":
                for keyword in ["Observation:", "Goal_Check:", "Reasoning:", "<cmd>"]:
                    formatted_response = re.sub(rf'(?i)({keyword})', r'\n\n\1', formatted_response)
                
                # Prepend the actual Memory injected in the prompt (before the new action)
                formatted_response = f"Memory:\n{mem_str_for_display}\n\n" + formatted_response.strip()
            
            # Normalize excessive newlines to exactly two
            formatted_response = re.sub(r'\n{3,}', '\n\n', formatted_response).strip()
            final_response = formatted_response

        total_time = time.time() - start_time
        inference_time = inference_end - inference_start
        
        ram_end = get_ram_usage()
        gpu_end = get_gpu_info()
        
        return {
            "response": final_response,
            "debug": {
                "total_time": f"{total_time:.2f}s",
                "inference_time": f"{inference_time:.2f}s",
                "load_time": f"{load_time:.2f}s",
                "ram_usage": f"{ram_start}% -> {ram_end}%",
                "gpu_usage": f"{gpu_start['percent']}% ({gpu_start['usage']}) -> {gpu_end['percent']}% ({gpu_end['usage']})",
                "device": "GPU" if (hasattr(model.device, 'type') and model.device.type == "cuda") or model.device == "cuda" else "CPU",
                "model_choice": model_choice
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
        
        # Pre-activate Qwen 3.5 bridge as requested
        ensure_bridge_server()
        
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
            # Apply persisted settings
            settings = load_settings()
            habitat_controller.set_height_offset(settings.get("height", 0.0))
            habitat_controller.clear_memory()
            
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
            return {
                "status": "success", 
                "frame": frame_base64,
                "collisions": habitat_controller.collision_count
            }
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
            habitat_controller.clear_memory()
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
            habitat_controller.clear_memory()
            return {"status": "success", "frame": frame_base64}
        except Exception as e:
            return {"status": "error", "message": str(e)}

@app.post("/spawn_starter")
async def spawn_starter():
    global habitat_controller
    with habitat_lock:
        if habitat_controller is None:
             return {"status": "error", "message": "Simulator not initialized"}
        try:
             success, frame = habitat_controller.spawn_starter()
             if success:
                 habitat_controller.clear_memory()
                 return {"status": "success", "frame": frame}
             else:
                 return {"status": "error", "message": "Failed to spawn"}
        except Exception as e:
             return {"status": "error", "message": str(e)}

@app.post("/update_height")
async def update_height(height: float = Form(...), locked: bool = Form(...)):
    global habitat_controller
    # Clamp height between -1.2m and 1.0m (max 1.0m as requested)
    clamped_height = max(-1.2, min(1.0, height))
    settings = {"height": clamped_height, "height_lock": locked}
    save_settings(settings)
    
    frame = None
    if habitat_controller:
        with habitat_lock:
            frame = habitat_controller.set_height_offset(clamped_height)
    
    return {
        "status": "success", 
        "message": f"Height updated to {clamped_height}m", 
        "locked": locked,
        "frame": frame
    }

@app.get("/get_settings")
async def get_settings_endpoint():
    return load_settings()

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
# --- OptiSight CoT Navigator Integration ---
autonomous_navigator = None

def do_inference_for_navigator(prompt, device_choice, model_choice):
    global habitat_controller, model, processor
    
    frame_b64 = habitat_controller.get_frame_as_base64()
    import base64
    image_data = base64.b64decode(frame_b64)
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    
    load_model_on_demand(device_choice, model_choice)
    
    if model_choice == "qwen2-2b":
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        from qwen_vl_utils import process_vision_info
        import torch
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to(model.device)

        with torch.no_grad():
            generated_ids = model.generate(
                **inputs, max_new_tokens=150, do_sample=True, temperature=0.1
            )
            
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        return output_text[0]
        
    elif model_choice in ["qwen3.5-0.8b", "qwen3.5-2b"]:
        import os, requests, config
        temp_image_path = os.path.join(os.getcwd(), "temp_auto_image.jpg")
        image.save(temp_image_path)
        
        target_path = config.QWEN35_08B_PATH if model_choice == "qwen3.5-0.8b" else config.QWEN35_2B_PATH
        api_payload = {
            "model_path": target_path,
            "image_path": temp_image_path,
            "prompt": prompt,
            "device": device_choice
        }
        resp = requests.post("http://127.0.0.1:8001/analyze", json=api_payload, timeout=120)
        result_data = resp.json()
        
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            
        if result_data.get("status") == "success":
            return result_data.get("response")
        else:
            raise Exception(f"Bridge Error: {result_data.get('message')}")
            
def do_move_for_navigator(action):
    global habitat_controller, autonomous_navigator
    if habitat_controller:
        prev_collisions = habitat_controller.collision_count
        frame = habitat_controller.move_agent(action)
        # Check if a collision occurred during this move
        if habitat_controller.collision_count > prev_collisions:
            if autonomous_navigator:
                autonomous_navigator.trigger_collision()
        return frame
    return None

@app.post("/start_autonomous_navigate")
async def start_autonomous_navigate(
    goal: str = Form(...),
    core_prompt: str = Form(None),
    searching_prompt: str = Form(None),
    navigating_prompt: str = Form(None),
    recovering_prompt: str = Form(None),
    device_choice: str = Form("cuda"),
    model_choice: str = Form("qwen2-2b"),
    execute_cmds: str = Form("true"),
    initial_state: str = Form("SEARCHING")
):
    global autonomous_navigator, habitat_controller
    if habitat_controller is None:
        return {"status": "error", "message": "Simulator not initialized"}
        
    execute_cmds_bool = execute_cmds.lower() == "true"
        
    if autonomous_navigator is None:
        autonomous_navigator = AutonomousNavigator(
            inference_callback=lambda p: do_inference_for_navigator(p, device_choice, model_choice),
            move_callback=do_move_for_navigator,
            execute_cmds=execute_cmds_bool
        )
        
    autonomous_navigator.inference_callback = lambda p: do_inference_for_navigator(p, device_choice, model_choice)
    autonomous_navigator.execute_cmds = execute_cmds_bool
    
    prompts = {
        "core": core_prompt,
        "searching": searching_prompt,
        "navigating": navigating_prompt,
        "recovering": recovering_prompt
    }
    # Filter out None
    prompts = {k: v for k, v in prompts.items() if v is not None}
    
    autonomous_navigator.update_settings(goal, prompts=prompts, initial_state=initial_state)
    
    return {"status": "success"}

@app.get("/autonomous_navigate_stream")
async def autonomous_navigate_stream():
    global autonomous_navigator
    if autonomous_navigator is None:
        return {"status": "error", "message": "Not started"}
    return StreamingResponse(autonomous_navigator.navigate_stream(), media_type="text/event-stream")
    
@app.post("/stop_autonomous_navigate")
async def stop_autonomous_navigate():
    global autonomous_navigator
    if autonomous_navigator:
        autonomous_navigator.set_running(False)
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
