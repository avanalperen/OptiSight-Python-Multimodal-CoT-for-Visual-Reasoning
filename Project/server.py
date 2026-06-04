import io
import os
import asyncio
import sys
import re
import json
import logging
import time
import base64
import requests
import psutil
import gc
import webbrowser
import subprocess
from collections import deque
from PIL import Image
import torch
import numpy as np
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from transformers import Qwen2VLForConditionalGeneration, AutoProcessor, Sam2Processor, Sam2Model
from qwen_vl_utils import process_vision_info
from autonomous_navigator import AutonomousNavigator
from vlm_visualizer import process_vlm_grounding
import config

try:
    from habitat_controller import HabitatController
    HABITAT_AVAILABLE = True
except ImportError:
    HabitatController = None
    HABITAT_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add Grounding DINO path
GD_PATH = r"C:\Alperen\IRI Internship\Open-Vocabulary Object Detectors\GroundingDINO-main"

# WSL Compatibility Check
if sys.platform != 'win32' or 'microsoft' in os.uname().release.lower():
    if GD_PATH.startswith('C:\\') or GD_PATH.startswith('c:\\'):
        GD_PATH = "/mnt/c/" + GD_PATH[3:].replace('\\', '/')

if GD_PATH not in sys.path:
    sys.path.append(GD_PATH)

try:
    from grounded_sam_pipeline import GroundedSAM
    import supervision as sv
except ImportError as e:
    logger.error(f"Grounded-SAM import failed: {e}")
    GroundedSAM = None


# Model Path
# Model Path
MODEL_PATH = config.MODEL_PATH

# Global model and processor
model = None
processor = None
sam_model = None
sam_processor = None
grounded_sam = None
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

async def run_grounded_sam(image, device_choice, text_prompt="door threshold, door frame, doorway, open door", scan_type=None):
    global grounded_sam
    from PIL import Image, ImageOps
    import io
    import numpy as np
    
    logger.info("--- [INTERNAL GROUNDED-SAM EXECUTION] ---")
    
    # Lazy load Grounded-SAM if needed
    if grounded_sam is None and GroundedSAM is not None:
        logger.info("Initializing Grounded-SAM module with absolute paths...")
        try:
            gd_config = os.path.join(GD_PATH, "groundingdino/config/GroundingDINO_SwinT_OGC.py")
            gd_weights = os.path.join(GD_PATH, "groundingdino_swint_ogc.pth")
            sam2_path = "/mnt/c/Alperen/IRI Internship/Vision Foundation Models/sam2.1-hiera-tiny"
            
            grounded_sam = GroundedSAM(
                gd_config_path=gd_config,
                gd_weights_path=gd_weights,
                sam2_path=sam2_path,
                device=device_choice
            )
            logger.info("Grounded-SAM module initialized successfully.")
        except Exception as e:
            logger.error(f"FAILED to initialize Grounded-SAM: {e}")
            return None, "Error: Grounded-SAM initialization failed.", None
    
    if grounded_sam is None:
        return None, "Error: Grounded-SAM not available.", None
 
    # --- NEW: Cleanup Old Debug Images to Prevent Stale Confusion ---
    debug_files = ["GROUNDING_SAM_INPUT.jpg", "1_DINO_OUTPUT.jpg", "2_SAM_OUTPUT.jpg", "sam_output.jpg", "input.jpg"]
    for dbg_file in debug_files:
        if os.path.exists(dbg_file):
            try: os.remove(dbg_file)
            except: pass
 
    try:
        # --- NEW: Padding Strategy for Edge Detection ---
        padding = 100
        # Expand image with white border (100px on all sides)
        padded_image = ImageOps.expand(image, border=padding, fill='white')
        
        logger.info(f"Executing Grounded-SAM predict with padding={padding} (Threaded)...")
        
        # --- FIX: Run blocking model call in a separate thread to prevent SSE timeout ---
        detections = await asyncio.to_thread(grounded_sam.predict, padded_image, text_prompt=text_prompt)
        logger.info(f"Prediction complete. Detections found in padded space: {len(detections.xyxy)}")
        
        angle_info = None
        final_response = "Grounded-SAM is scanning for door threshold. No definitive detection yet."
        
        if detections is not None and len(detections.xyxy) > 0:
            # --- Transform Detections back to Original Coordinate Space ---
            W, H = image.size
            
            # 1. Shift Bounding Boxes
            detections.xyxy -= padding
            # Clip boxes to image boundaries
            detections.xyxy[:, [0, 2]] = np.clip(detections.xyxy[:, [0, 2]], 0, W)
            detections.xyxy[:, [1, 3]] = np.clip(detections.xyxy[:, [1, 3]], 0, H)
            
            # 2. Crop Masks
            if detections.mask is not None:
                # detections.mask shape is (N, H_padded, W_padded)
                detections.mask = detections.mask[:, padding:padding+H, padding:padding+W]
            
            # Take the best detection
            best_idx = np.argmax(detections.confidence)
            box = detections.xyxy[best_idx]
            conf = detections.confidence[best_idx]
            
            logger.info(f"Best Match Found (Mapped back): Box={box}, Confidence={conf:.2f}")

            # Convert to normalized 0-1 for navigation logic
            x_min, y_min, x_max, y_max = box[0]/W, box[1]/H, box[2]/W, box[3]/H
            
            # Use global or session-based HFOV
            hfov_to_use = 90
            if habitat_controller:
                hfov_to_use = habitat_controller.hfov

            angle = calculate_angle(x_min, x_max, hfov=hfov_to_use)
            range_label = get_angle_range_label(angle)
            angle_info = {
                "angle": round(angle, 2),
                "range": range_label,
                "box": {
                    "x_min": float(x_min),
                    "y_min": float(y_min),
                    "x_max": float(x_max),
                    "y_max": float(y_max)
                }
            }
            final_response = f"Door threshold successfully identified with {conf:.2f} confidence. Spatial coordinates extracted for visual servoing."
            
            # --- Generate Step-by-Step Outputs (Debugging) ---
            try:
                import cv2
                import glob
                # Note: We annotate the ORIGINAL (un-padded) image
                if 'image_cv' not in locals():
                    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # 1. Save DINO Output (Box only)
                box_annotator = sv.BoxAnnotator()
                best_detection = detections[best_idx : best_idx + 1]
                dino_frame = box_annotator.annotate(scene=image_cv.copy(), detections=best_detection)
                cv2.imwrite("1_DINO_OUTPUT.jpg", dino_frame)
                
                # 2. Save SAM Output (Mask + Box)
                mask_annotator = sv.MaskAnnotator()
                sam_frame = mask_annotator.annotate(scene=dino_frame.copy(), detections=best_detection)
                cv2.imwrite("2_SAM_OUTPUT.jpg", sam_frame)
                
                # --- Custom Obstacle scan screenshots ---
                if scan_type in ["tilted", "obstacle"]:
                    test_dir = r"C:\Alperen\IRI Internship\My Project\Project\ObstacleDINO+SAM TEST"
                    if sys.platform != 'win32' or 'microsoft' in os.uname().release.lower():
                        if test_dir.startswith('C:\\') or test_dir.startswith('c:\\'):
                            test_dir = "/mnt/c/" + test_dir[3:].replace('\\', '/')
                    os.makedirs(test_dir, exist_ok=True)
                    
                    # Sequence numbering
                    import glob
                    dino_pattern = os.path.join(test_dir, f"DINO_{scan_type}_*.jpg")
                    existing_files = glob.glob(dino_pattern)
                    next_num = 1
                    if existing_files:
                        nums = []
                        for f in existing_files:
                            try:
                                base = os.path.basename(f)
                                num_part = base.split("_")[-1].split(".")[0]
                                nums.append(int(num_part))
                            except:
                                continue
                        if nums:
                            next_num = max(nums) + 1
                            
                    dino_name = os.path.join(test_dir, f"DINO_{scan_type}_{next_num:02d}.jpg")
                    sam_name = os.path.join(test_dir, f"SAM_{scan_type}_{next_num:02d}.jpg")
                    
                    cv2.imwrite(dino_name, dino_frame)
                    cv2.imwrite(sam_name, sam_frame)
                    logger.info(f"SUCCESS: Saved custom scan outputs: {dino_name} and {sam_name}")
                else:
                    logger.info("SUCCESS: All Grounded-SAM debug outputs (1_DINO_OUTPUT.jpg, 2_SAM_OUTPUT.jpg) generated on ORIGINAL frame.")
            except Exception as e:
                logger.error(f"Failed to generate debug outputs: {e}")
        
        return detections, final_response, angle_info

    except Exception as e:
        logger.error(f"Grounded-SAM Pipeline CRASHED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, f"Error: Grounded-SAM pipeline crashed: {e}", None

def get_ram_usage():
    return psutil.virtual_memory().percent

def calculate_angle(x_min, x_max, hfov=90):
    # center_x is 0-1 normalized
    center_x = (x_min + x_max) / 2
    
    # Perspektif-doğru (non-linear) conversion:
    # theta = atan((center_x - 0.5) * 2 * tan(hfov/2))
    half_fov_rad = np.deg2rad(hfov / 2)
    offset_from_center = (center_x - 0.5) * 2 # maps 0..1 to -1..1
    
    angle_rad = np.arctan(offset_from_center * np.tan(half_fov_rad))
    angle_deg = np.rad2deg(angle_rad)
    
    return angle_deg

def get_angle_range_label(angle):
    if angle < -30: return "FAR_LEFT"
    if angle < -10: return "LEFT"
    if angle < 10: return "CENTER"
    if angle < 30: return "RIGHT"
    return "FAR_RIGHT"

# Global Habitat Controller
habitat_controller = None
import threading
habitat_lock = asyncio.Lock()
# Absolute paths for persistent files to ensure they remain even if server is started from different CWD
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
SCENARIOS_FILE = os.path.join(BASE_DIR, "scenarios.json")
SESSION_SETTINGS = {"height": 0.0, "height_lock": False}

def load_scenarios():
    default_scenarios = {
        'scenario1': {
            'core': "",
            'searching': "",
            'finding': "",
            'scanning': "",
            'navigating': "",
            'stopping': "",
            'recovering': ""
        },
        'scenario2': {
            'core': "",
            'searching': "",
            'finding': "",
            'scanning': "",
            'navigating': "",
            'stopping': "",
            'recovering': ""
        }
    }
    if os.path.exists(SCENARIOS_FILE):
        try:
            with open(SCENARIOS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.error(f"Error loading scenarios: {e}")
    return default_scenarios

SCENARIO_PROMPTS_DIR = os.path.join(os.getcwd(), "scenario prompts")

def save_scenarios(scenarios):
    try:
        # 1. Save main JSON (Source of Truth)
        with open(SCENARIOS_FILE, "w", encoding="utf-8") as f:
            json.dump(scenarios, f, indent=4)
        
        # 2. Systematic Save to individual .txt files
        if not os.path.exists(SCENARIO_PROMPTS_DIR):
            os.makedirs(SCENARIO_PROMPTS_DIR)
            
        for scenario_id, prompts in scenarios.items():
            scenario_path = os.path.join(SCENARIO_PROMPTS_DIR, scenario_id)
            if not os.path.exists(scenario_path):
                os.makedirs(scenario_path)
            
            for prompt_type, content in prompts.items():
                file_name = f"{prompt_type}.txt"
                file_path = os.path.join(scenario_path, file_name)
                with open(file_path, "w", encoding="utf-8") as f:
                    # Filter out placeholders or empty content if needed, but here we save exactly what we have
                    f.write(content if content else "")
                    
        return True
    except Exception as e:
        logger.error(f"Error saving scenarios: {e}")
        return False

def load_settings():
    default_settings = {
        "height": 0.0, 
        "height_lock": False, 
        "autonav_target": "Go Through the door",
        "autonav_initial_state": "SEARCHING"
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure all default keys exist
                for k, v in default_settings.items():
                    if k not in data:
                        data[k] = v
                # FORCE RESET: If height is -1.2 (stuck state), reset to 0.0
                if data.get("height") == -1.2:
                    data["height"] = 0.0
                return data
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
    return default_settings

def save_settings(settings):
    try:
        current = load_settings()
        current.update(settings)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

def sync_prompts_to_filesystem(scenarios):
    """Syncs the latest prompts from scenario1 to designated 'best' text files."""
    try:
        # Core prompt sync
        core_path = os.path.join("core prompts", "best", "Best Core Prompt.txt")
        os.makedirs(os.path.dirname(core_path), exist_ok=True)
        
        # State prompts mapping
        state_paths = {
            'searching': os.path.join("scenario prompts", "searching", "Best Searching Prompt.txt"),
            'finding': os.path.join("scenario prompts", "finding", "Best Finding Prompt.txt"),
            'navigating': os.path.join("scenario prompts", "navigating", "Best Navigating Prompt.txt"),
            'stopping': os.path.join("scenario prompts", "stopping", "Best Stopping Prompt.txt"),
            'recovering': os.path.join("scenario prompts", "recovering", "Best Recovering Prompt.txt")
        }
        
        # We take prompts from 'scenario1' as the primary source for sync
        s1 = scenarios.get('scenario1', {})
        
        # Sync Core
        if s1.get('core'):
            with open(core_path, "w", encoding="utf-8") as f:
                f.write(s1['core'])
            logger.info(f"Synced Best Core Prompt to {core_path}")
            
        # Sync States
        for state, path in state_paths.items():
            if s1.get(state):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(s1[state])
                logger.info(f"Synced Best {state.capitalize()} Prompt to {path}")
                
    except Exception as e:
        logger.error(f"Error syncing prompts to filesystem: {e}")

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

# Custom filter to change 0.0.0.0 to localhost in uvicorn startup message
class UvicornURLFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if "Uvicorn running on" in record.msg and record.args and len(record.args) >= 2 and record.args[1] == "0.0.0.0":
            new_args = list(record.args)
            new_args[1] = "localhost"
            record.args = tuple(new_args)
        return True

# Apply filter to uvicorn access logs
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
logging.getLogger("uvicorn.error").addFilter(UvicornURLFilter())

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
            # Sync to best text files
            sync_prompts_to_filesystem(data)
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Failed to save file"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/clear_habitat_memory")
async def clear_habitat_memory():
    global habitat_controller
    if habitat_controller:
        async with habitat_lock:
            habitat_controller.clear_memory()
        logger.info("Habitat memory cleared via endpoint.")
        return {"status": "success", "message": "Memory cleared."}
    return {"status": "error", "message": "Simulator not initialized."}

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

def preload_grounded_sam(device_choice="cuda"):
    global grounded_sam
    if grounded_sam is not None:
        return 0, device_choice
    
    start_load = time.time()
    logger.info(f"Pre-loading Grounded-SAM (DINO + SAM 2.1) on {device_choice}...")
    
    try:
        gd_config = os.path.join(GD_PATH, "groundingdino/config/GroundingDINO_SwinT_OGC.py")
        gd_weights = os.path.join(GD_PATH, "groundingdino_swint_ogc.pth")
        sam2_path = "/mnt/c/Alperen/IRI Internship/Vision Foundation Models/sam2.1-hiera-tiny"
        
        grounded_sam = GroundedSAM(
            gd_config_path=gd_config,
            gd_weights_path=gd_weights,
            sam2_path=sam2_path,
            device=device_choice
        )
        load_time = time.time() - start_load
        logger.info(f"Grounded-SAM pre-loaded successfully in {load_time:.2f}s (Status: IDLE)")
        return load_time, device_choice
    except Exception as e:
        logger.error(f"Failed to pre-load Grounded-SAM: {e}")
        grounded_sam = None
        return 0, device_choice

async def load_model_on_demand(device_choice="cpu", model_choice="qwen2-2b"):
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
            async with habitat_lock:
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
                trust_remote_code=True,
                min_pixels=16*28*28,
                max_pixels=1024*28*28
            )
            # Pre-load Grounded-SAM simultaneously in the same process
            sam_time, sam_device = preload_grounded_sam(device_choice)
            vlm_time = time.time() - start_load
            vlm_device = device_choice
        elif model_choice in ["qwen3.5-0.8b", "qwen3.5-2b"]:
            # Ensure the bridge server is running
            ensure_bridge_server()
            
            # Explicitly trigger load in bridge server to get timings
            try:
                resp = requests.post("http://127.0.0.1:8001/load", json={
                    "model_path": target_model_path,
                    "device": device_choice
                }, timeout=300)
                info = resp.json()
                if info.get("status") == "success":
                    vlm_time = info.get("vlm_time", 0)
                    vlm_device = info.get("vlm_device", device_choice)
                    sam_time = info.get("sam_time", 0)
                    sam_device = info.get("sam_device", device_choice)
                else:
                    raise Exception(info.get("message", "Bridge load failed"))
            except Exception as e:
                logger.error(f"Failed to load through bridge: {e}")
                vlm_time = 0
                vlm_device = device_choice
                sam_time = 0
                sam_device = device_choice

            # For Qwen 3.5, we don't load in this process (uses bridge script)
            model = type('MockModel', (), {'loaded_model_choice': model_choice, 'device': device_choice})()
            processor = None
            logger.info(f"{model_choice} managed via persistent bridge server.")
        
        model.loaded_model_choice = model_choice  # Track the loaded model
        
        return {
            "vlm_model": model_choice,
            "vlm_device": vlm_device,
            "vlm_time": vlm_time,
            "sam_model": "SAM 2.1 Tiny",
            "sam_device": sam_device,
            "sam_time": sam_time
        }
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        model = None
        processor = None
        raise e

@app.post("/load_model")
async def load_model_endpoint(device_choice: str = Form("cuda"), model_choice: str = Form("qwen2-2b")):
    try:
        info = await load_model_on_demand(device_choice, model_choice)
        msg = (f"{info['vlm_model']} loaded on {info['vlm_device']} ({info['vlm_time']:.1f}s). "
               f"{info['sam_model']} pre-loaded on {info['sam_device']} ({info['sam_time']:.1f}s).")
        return {"status": "success", "message": msg}
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
    
    global grounded_sam
    if grounded_sam is not None:
        try:
            del grounded_sam
        except:
            pass
        grounded_sam = None
        
    # Force Python GC and CUDA cleanups multiple times
    import gc
    for _ in range(3):
        gc.collect()
        if torch.cuda.is_available():
            async with habitat_lock:
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
    
    # Wait briefly for NVIDIA drivers to update their memory reporting
    import time
    await asyncio.sleep(1.0)
            
    logger.info("Model unloaded from memory. Cleanup complete.")
    return {"status": "success", "message": "Model unloaded from memory."}

@app.post("/set_state")
async def set_state(state: str = Form(...)):
    global autonomous_navigator
    if autonomous_navigator is None:
        logger.info("Navigator not initialized. Creating default instance for state management.")
        autonomous_navigator = AutonomousNavigator(
            inference_callback=lambda p: "MANUAL_STATE_SYNC",
            move_callback=do_move_for_navigator,
            execute_cmds=True
        )
        
    target_state = state.upper()
    if target_state == "SCANNING":
        target_state = "SCANNING_PATH"
    autonomous_navigator.state = target_state
    autonomous_navigator.pass_sequence_triggered = False # Reset pass trigger on every manual state change
    
    if autonomous_navigator.state == "SEARCHING":
        autonomous_navigator.locked_bbox = None
    
    if autonomous_navigator.state == "NAVIGATING" and habitat_controller:
        # Capture current pose to restore if we collide during alignment
        autonomous_navigator.navigating_start_pose = habitat_controller.agent.get_state()
        logger.info("Navigation start pose captured.")
        
    logger.info(f"State manually set to: {autonomous_navigator.state}")
    return {"status": "success", "state": autonomous_navigator.state}

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    goal: str = Form(None),
    device_choice: str = Form("cpu"),
    model_choice: str = Form("qwen2-2b"),
    habitat_submode: str = Form(None),
    memory_mode: str = Form("true"),
    bbox_mode: str = Form("false"),
    angle_grid_mode: str = Form("false"), # NEW: Pass angle grid state
    state: str = Form("CORE"),
    is_fullscreen: str = Form("false")
):
    global model, processor, habitat_controller, grounded_sam
    
    import time
    start_time = time.time()
    logger.info(f"--- [ANALYZE REQUEST] State: {state} | SubMode: {habitat_submode} | BBox: {bbox_mode} | Model: {model_choice} ---")
    mem_str_for_display = "None"
    grounded_sam_active = False
    angle_info = None
    
    try:
        # --- GROUNDED-SAM BYPASS LOGIC ---
        # Trigger ONLY in FINDING state when legacy modes are OFF
        if state.upper() == "FINDING":
            logger.info(f"FINDING State Detected. Checking Bypass Conditions: BBox={bbox_mode}, AngleGrid={angle_grid_mode}")
            
            if bbox_mode.lower() == "false" and angle_grid_mode.lower() == "false":
                logger.info("Conditions Met: Grounded-SAM pipeline triggered (VLM bypass).")
                
                contents = await file.read()
                image = Image.open(io.BytesIO(contents)).convert("RGB")
                
                # Resize image for Grounded-SAM efficiency (matches VLM resize)
                max_size = 1080 if is_fullscreen.lower() == "true" else 672
                if max(image.size) > max_size:
                    ratio = max_size / max(image.size)
                    new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)
                    logger.info(f"Resized image to {new_size} for Grounded-SAM efficiency.")
                
                detections, final_response, angle_info = await run_grounded_sam(image, device_choice)
                
                if detections is not None:
                    grounded_sam_active = True

                return {
                    "response": final_response,
                    "grounded_sam_active": grounded_sam_active,
                    "angle_info": angle_info,
                    "debug": {
                        "total_time": f"{time.time() - start_time:.2f}s",
                        "load_time": "0.00s",
                        "inference_time": f"{time.time() - start_time:.2f}s",
                        "ram_usage": "N/A (Skipped for Speed)",
                        "gpu_usage": "N/A (Skipped for Speed)",
                        "model_choice": "Grounded-SAM (DINO+SAM2.1)",
                        "device": device_choice
                    }
                }
        
        # --- Standard VLM Flow ---
        # 1. Prompt Injection - Handle memory system and goal
        # Replace {goal} if provided
        if goal:
            prompt = prompt.replace("{goal}", goal)
            logger.info(f"Replaced {{goal}} with: {goal}")
            
        prompt = prompt.replace("{current_state}", state)

        if ("{PREVIOUS_MEMORY}" in prompt or "{memory}" in prompt) and habitat_controller:
            if memory_mode.lower() == "true":
                mem_str = habitat_controller.get_memory_string()
                prompt = prompt.replace("{PREVIOUS_MEMORY}", mem_str).replace("{memory}", mem_str)
                logger.info("Injected memory into prompt.")
            else:
                prompt = prompt.replace("Previous memory: {PREVIOUS_MEMORY}.", "")
                prompt = prompt.replace("{PREVIOUS_MEMORY}", "None").replace("{memory}", "None")
                logger.info("Memory mode disabled, omitted memory from prompt.")
                
        # On-demand loading
        load_time = await load_model_on_demand(device_choice, model_choice)
        
        ram_start = get_ram_usage()
        gpu_start = get_gpu_info()
        logger.info(f"--- Analysis Started ---")
        logger.info(f"Model Choice: {model_choice} | Device: {device_choice} (Load Time: {load_time:.2f}s)")
        logger.info("Prompt Injected.")
        
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # DEBUG: Save the exact image being sent to the VLM so the user can verify grid presence
        debug_path = os.path.join(os.getcwd(), "vlm_input_debug.jpg")
        image.save(debug_path)
        logger.info(f"VLM Debug Image saved to {debug_path}")
        
        max_size = 1080 if is_fullscreen.lower() == "true" else 672
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Apply Sharpening to improve OCR/Number readability
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0) # 2.0 is a solid sharpening factor
            
        # Save SECOND debug image (Optimized/Resized) - Exactly what VLM receives
        optimized_debug_path = os.path.join(os.getcwd(), "vlm_optimized_input_debug.jpg")
        image.save(optimized_debug_path)
        logger.info(f"VLM Optimized Debug Image saved to {optimized_debug_path}")
        
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
        # Transition logic should work if habitat_controller is available, even if submode is not explicitly set
        if habitat_controller:
            # Capture the memory state BEFORE we append the new action
            mem_str_for_display = habitat_controller.get_memory_string()
            
            # Sentence extraction for Reasoning
            reasoning_match = re.search(r'Reasoning:\s*(.*?)(?=\. <cmd>|$)', final_response, re.IGNORECASE)
            # If standard regex fails, look for 'Reasoning:' until the end or first period
            if not reasoning_match:
                reasoning_match = re.search(r'Reasoning:\s*(.*?)(?=\.|$)', final_response, re.IGNORECASE)
            
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "Reasoning omitted."
            
            # Goal Check extraction: Goal_Check: YES/NO
            goal_check_match = re.search(r'Goal_Check:\s*(.*?)(?=\n|Plan:|$)', final_response, re.IGNORECASE)
            goal_check = goal_check_match.group(1).strip() if goal_check_match else "UNKNOWN"
            
            # Command extraction: <cmd>...</cmd>
            command_match = re.search(r'<cmd>(.*?)</cmd>', final_response, re.IGNORECASE)
            extracted_cmd = None
            
            # Fallback for bare Yes/No responses in SEARCHING state
            if state.upper() == "SEARCHING" and goal_check == "UNKNOWN":
                clean_resp = final_response.strip().upper()
                if "YES" in clean_resp: goal_check = "YES"
                elif "NO" in clean_resp: goal_check = "NO"
            
            # SEARCHING Mode Logic: Automatic turn on NO or transition on YES
            next_state = None
            system_info = None
            
            logger.info(f"State Check: Current={state}, Goal_Check={goal_check}")
            
            current_frame = None
            if state.upper() == "SEARCHING":
                if goal_check.upper() == "NO":
                    logger.info("SEARCHING STATE: Goal not found. Signaling frontend for smooth search turn.")
                    # Return signal for frontend to execute steps smoothly
                    system_info = "START_SEARCH_TURN"
                    reasoning = "[System] Goal not visible. Rotating to scan..."
                    # Just return current frame
                    async with habitat_lock:
                        current_frame = habitat_controller.get_frame_as_base64()
                elif goal_check.upper() == "YES":
                    logger.info("SEARCHING STATE: Goal found! Transitioning to FINDING.")
                    next_state = "FINDING"
                    system_info = "Goal spotted!"
                    reasoning = "[System] " + system_info
                    # Capture current frame for UI
                    async with habitat_lock:
                        current_frame = habitat_controller.get_frame_as_base64()
            
            # Ensure next_state is captured even if command_match is None
            if next_state:
                logger.info(f"Next State set to: {next_state}")

            if command_match or (state.upper() == "SEARCHING" and goal_check.upper() == "NO"):
                extracted_cmd = extracted_cmd if (state.upper() == "SEARCHING" and goal_check.upper() == "NO") else command_match.group(1).strip()
                logger.info(f"System identified action: {extracted_cmd} | State: {state}")
                
                # Update persistent memory within the core controller
                habitat_controller.record_vlm_action(extracted_cmd, reasoning, state=state)
                
                # Execute movement immediately in simulator for 'autonomous' mode
                # For 'SEARCHING' + 'NO', we already executed it above.
                if habitat_submode == 'autonomous' and not (state.upper() == "SEARCHING" and goal_check.upper() == "NO"):
                    async with habitat_lock:
                        logger.info(f"AUTONOMOUS EXECUTION: {extracted_cmd}")
                        habitat_controller.move_agent(extracted_cmd)

        # 3. Clean and format the final response for display
        if habitat_submode in ['live', 'live_one_shot', 'autonomous'] and habitat_controller:
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
        
        # --- NEW: Bounding Box Visualization (RESTRICTED TO HABITAT + BBOX) ---
        bbox_data = parse_vlm_box(final_response)
        angle_info = None
        
        if bbox_data:
            angle = calculate_angle(bbox_data['x_min'], bbox_data['x_max'])
            range_label = get_angle_range_label(angle)
            angle_info = {
                "angle": round(angle, 2),
                "range": range_label,
                "box": bbox_data
            }
            # angle_info is sent separately, no need to append to text anymore
            # final_response += f"\n\n[Calculated Angle: {round(angle, 2)}° | Range: {range_label}]"

            # ONLY generate output.jpg if in Habitat modes AND state is FINDING AND Bounding Box toggle is Active
            if habitat_submode in ['live', 'live_one_shot', 'autonomous'] and habitat_controller and state.upper() == 'FINDING' and bbox_mode.lower() == 'true':
                try:
                    # Use the existing optimized debug image as source
                    source_img = "vlm_optimized_input_debug.jpg"
                    if os.path.exists(source_img):
                        process_vlm_grounding(source_img, final_response, "output.jpg")
                        logger.info(f"Successfully generated output.jpg for FINDING state using {source_img}")
                    else:
                        # Fallback if debug image doesn't exist yet
                        temp_viz = "temp_viz_fallback.jpg"
                        image.save(temp_viz)
                        process_vlm_grounding(temp_viz, final_response, "output.jpg")
                        logger.info("Generated output.jpg using fallback image.")
                except Exception as e:
                    logger.error(f"Visualization error: {e}")

        return {
            "response": final_response,
            "next_state": next_state,
            "system_info": system_info,
            "frame": current_frame,
            "injected_memory": mem_str_for_display,
            "angle_info": angle_info,
            "grounded_sam_active": grounded_sam_active,
            "debug": {
                "total_time": f"{total_time:.2f}s",
                "inference_time": f"{inference_time:.2f}s",
                "load_time": f"{load_time:.2f}s",
                "ram_usage": f"{ram_start}% -> {ram_end}%",
                "gpu_usage": f"{gpu_start['percent']}% ({gpu_start['usage']}) -> {gpu_end['percent']}% ({gpu_end['usage']})",
                "device": "GPU" if (hasattr(model.device, 'type') and model.device.type == "cuda") or model.device == "cuda" else "CPU",
                "model_choice": model_choice,
                "final_prompt": prompt
            }
        }

    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        return {"response": f"Error: {str(e)}"}

# --- Habitat Routes ---

@app.get("/list_scenes")
async def list_scenes():
    scene_dir = os.path.join(os.getcwd(), "test habitats")
    if not os.path.exists(scene_dir):
        return {"scenes": []}
    scenes = [f for f in os.listdir(scene_dir) if f.endswith('.glb') or f.endswith('.json')]
    return {"scenes": sorted(scenes)}

@app.post("/init_sim")
async def init_sim(
    file: UploadFile = File(None), 
    scene_name: str = Form(None),
    width: int = Form(1920),
    height: int = Form(1080),
    hfov: float = Form(90)
):
    global habitat_controller
    if not HABITAT_AVAILABLE:
        return {"status": "error", "message": "Habitat Sim is not installed or supported on this system."}
    
    try:
        if file:
            # Save uploaded file to test habitats
            upload_dir = os.path.join(os.getcwd(), "test habitats")
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, file.filename)
            contents = await file.read()
            with open(filepath, "wb") as f:
                f.write(contents)
            scene_to_use = filepath
            logger.info(f"Using uploaded scene: {scene_to_use}")
        elif scene_name:
            scene_to_use = os.path.join(os.path.join(os.getcwd(), "test habitats"), scene_name)
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

        async with habitat_lock:
            # Pass width, height, and hfov to controller
            sim_settings["width"] = width
            sim_settings["height"] = height
            sim_settings["hfov"] = hfov
            habitat_controller = HabitatController(scene_to_use, **sim_settings)
            # Apply persisted settings
            settings = load_settings()
            habitat_controller.set_height_offset(settings.get("height", 0.0))
            habitat_controller.clear_memory()
            
            # Initialize default Navigator for state tracking in manual mode
            global autonomous_navigator
            autonomous_navigator = AutonomousNavigator(
                inference_callback=lambda p: "MANUAL_INIT",
                move_callback=do_move_for_navigator,
                execute_cmds=True
            )
            
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

@app.post("/save_screenshot")
async def save_screenshot(request: Request):
    try:
        data = await request.json()
        image_data = data.get("image")
        prefix = data.get("prefix", "Screenshot")
        
        # Ensure prefix is clean and safe
        if prefix not in ["Screenshot", "Autonomous_Screenshot", "Autonomous_Screenshout"]:
            prefix = "Screenshot"
            
        # Correct typo spelling of Screenshout to Screenshot
        if prefix == "Autonomous_Screenshout":
            prefix = "Autonomous_Screenshot"
            
        if not image_data:
            return {"status": "error", "message": "No image data provided"}
            
        # Decode base64 image
        if "," in image_data:
            header, encoded = image_data.split(",", 1)
        else:
            encoded = image_data
            
        binary_data = base64.b64decode(encoded)
        
        # Sequentially number screenshots based on prefix
        import glob
        import os
        
        existing = glob.glob(f"{prefix}_*.jpg")
        nums = [0]
        for f in existing:
            try:
                # Extract number from prefix_XX.jpg
                base = os.path.basename(f)
                num_part = base.replace(f"{prefix}_", "").split(".")[0]
                nums.append(int(num_part))
            except:
                continue
        
        next_num = max(nums) + 1
        filename = f"{prefix}_{next_num:02d}.jpg"
        
        with open(filename, "wb") as f:
            f.write(binary_data)
            
        logger.info(f"Screenshot saved successfully: {filename}")
        return {"status": "success", "filename": filename}
    except Exception as e:
        logger.error(f"Error saving screenshot: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/start_3d_projection")
async def start_3d_projection(request: Request):
    global habitat_controller
    try:
        data = await request.json()
        bbox = data.get("bbox")
        if habitat_controller and bbox:
            async with habitat_lock:
                success = habitat_controller.start_3d_projection([
                    bbox["x_min"], bbox["y_min"], bbox["x_max"], bbox["y_max"]
                ])
                if success:
                    # Also immediately get initial projection to render
                    initial_proj = habitat_controller.get_projected_3d_points()
                    return {"status": "success", "projection_info": initial_proj}
        return {"status": "error", "message": "Failed to start 3D projection"}
    except Exception as e:
        logger.error(f"3D projection start error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/move")
async def move_agent(command: str = Form(...)):
    global habitat_controller, autonomous_navigator

    if habitat_controller is None:
        return {"status": "error", "message": "Simulator not initialized"}
    
    if autonomous_navigator is None:
        autonomous_navigator = AutonomousNavigator(
            inference_callback=lambda p: do_inference_for_navigator(p, "cuda", "qwen2-2b"),
            move_callback=do_move_for_navigator,
            execute_cmds=True
        )
    
    try:
        tracking_info = None
        async with habitat_lock:
            # Record pose history (up to 5 steps back) - Only if position/rotation changed
            if autonomous_navigator and command not in ["restore_nav_start", "pop_and_restore_pose", "refresh"]:
                curr_state = habitat_controller.agent.get_state()
                is_unique = True
                if autonomous_navigator.pose_history:
                    last_pose = autonomous_navigator.pose_history[-1]
                    dist = np.linalg.norm(curr_state.position - last_pose.position)
                    # Quaternions cannot be subtracted directly for norm; use equality or component check
                    is_same_rot = (curr_state.rotation == last_pose.rotation)
                    if dist < 0.01 and is_same_rot:
                        is_unique = False
                
                if is_unique:
                    autonomous_navigator.pose_history.append(curr_state)
                
            # Handle special auto_align command for manual mode automated steps
            if command == "auto_align" and autonomous_navigator:
                proj = habitat_controller.get_projected_3d_points()
                align_cmd = autonomous_navigator.get_auto_align_command(proj)
                
                # Detailed logging for alignment decision
                proj_status = "ACTIVE" if proj and proj.get("corners") else "EMPTY"
                logger.info(f"Auto-Align Request | 3D Proj: {proj_status} | Decision: {align_cmd} | Current State: {autonomous_navigator.state}")
                
                # "Dümdüz ilerlemeli" logic: Always advance, but adjust heading if needed
                if "turn" in align_cmd:
                    habitat_controller.move_agent(align_cmd) # Apply fine turn
                    command = "move_forward" # Continue to move forward
                else:
                    command = align_cmd

            # Special recovery command: POP the last good pose and restore it (for step-by-step rewind)
            if command == "pop_and_restore_pose" and autonomous_navigator:
                if autonomous_navigator.pose_history:
                    safe_pose = autonomous_navigator.pose_history.pop()
                    logger.info(f"Recovery: Rewinding to previous pose. History remaining: {len(autonomous_navigator.pose_history)}")
                    habitat_controller.agent.set_state(safe_pose)
                    habitat_controller._apply_height_offset()
                command = "refresh"

            # Fallback legacy recovery command
            if command == "restore_nav_start" and autonomous_navigator:
                if autonomous_navigator.navigating_start_pose:
                    logger.info("Recovery: Restoring to navigation start pose.")
                    habitat_controller.agent.set_state(autonomous_navigator.navigating_start_pose)
                    habitat_controller._apply_height_offset()
                    autonomous_navigator.pose_history.clear()
                command = "refresh"

            last_col = habitat_controller.collision_count
        
        # Smoothing for manual 90-degree turns to match neck-turning effect
        if "90" in command and "turn" in command:
            base_dir = "turn_left" if "left" in command else "turn_right"
            logger.info(f"Manual Mode: Smoothing {command} into 9 steps...")
            frame_base64 = None
            for i in range(9):
                async with habitat_lock:
                    frame_base64 = habitat_controller.move_agent(base_dir)
                # RELEASE lock during sleep to allow other requests (like logs/frames) to pass through
                await asyncio.sleep(0.3)
        else:
            async with habitat_lock:
                frame_base64 = habitat_controller.move_agent(command)
            
        if autonomous_navigator:
            autonomous_navigator.last_command = command
            
            # Check if this move caused a new collision
            if habitat_controller.collision_count > last_col:
                logger.warning("Manual collision detected! Initiating automatic recovery.")
                autonomous_navigator.state = "RECOVERING"
                
                # Delegate the recovery sequence to the frontend for visual feedback
                tracking_info = f"START_RECOVERY:{command}"
        
        # If a servoing state is active, update tracking in the background
        if autonomous_navigator and tracking_info is None:
            # Include current projection info for state transition logic (e.g. passing door)
            proj_info = habitat_controller.get_projected_3d_points()
            frame_base64, tracking_info = autonomous_navigator.process_manual_step(frame_base64, proj_info)
            if tracking_info:
                logger.info(f"Step Tracking | State: {autonomous_navigator.state} | Info: {tracking_info if isinstance(tracking_info, str) else 'Spatial Object'}")
            
            # NEW: Automatic clearing sequence upon threshold detection in Manual Mode
            if tracking_info == "PASS_DETECTED":
                # Delegate the 5 steps to the frontend for visual feedback (non-teleporting)
                tracking_info = "START_CLEARING"

        projection_info = habitat_controller.get_projected_3d_points()

        return {
            "status": "success", 
            "frame": frame_base64,
            "tracking_info": tracking_info,
            "projection_info": projection_info,
            "collisions": habitat_controller.collision_count,
            "state": autonomous_navigator.state if autonomous_navigator else None
        }
    except Exception as e:
        logger.error(f"Movement error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/get_map")
async def get_map():
    global habitat_controller
    async with habitat_lock:
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
    async with habitat_lock:
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

    async with habitat_lock:
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
    async with habitat_lock:
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
    async with habitat_lock:
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
    async with habitat_lock:
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
        async with habitat_lock:
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

@app.post("/save_target")
async def save_target(target: str = Form(...)):
    save_settings({"autonav_target": target})
    return {"status": "success"}

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

def apply_angle_grid(image):
    from PIL import ImageDraw, ImageFont
    import math
    draw = ImageDraw.Draw(image)
    width, height = image.size
    
    hfov = 90
    angles = [-40, -30, -20, -10, 0, 10, 20, 30, 40]
    half_fov_rad = (hfov / 2) * math.pi / 180
    
    # Thinner lines and labels at the top to avoid obscuring the target
    line_width = 8 
    font_size = 60 
    
    try:
        # Search for common fonts across systems - Prioritize Arial Bold to fix slashed zero issue
        font = None
        for f_name in ["arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"]:
            try:
                font = ImageFont.truetype(f_name, font_size)
                break
            except: continue
        if not font: font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    for angle in angles:
        theta = angle * math.pi / 180
        left_percent = 50 + 50 * math.tan(theta) / math.tan(half_fov_rad)
        x = width * (left_percent / 100)
        
        # Draw thin bright green line
        draw.line([(x, 0), (x, height)], fill=(0, 255, 0), width=line_width)
        
        # Draw label at y=60 with a robust black outline for VLM readability
        text = f"{angle}°"
        y_pos = 60
        outline_color = (0, 0, 0)
        text_color = (0, 255, 0)
        
        # Draw outline by offsetting in 8 directions
        for ox in [-2, 0, 2]:
            for oy in [-2, 0, 2]:
                if ox == 0 and oy == 0: continue
                draw.text((x + ox, y_pos + oy), text, fill=outline_color, font=font, anchor="mt")
        
        # Main text
        draw.text((x, y_pos), text, fill=text_color, font=font, anchor="mt")

    
    return image

def parse_vlm_box(text):
    """
    Parses <box>(X_min, Y_min), (X_max, Y_max)</box> from VLM response.
    Returns normalized values (0-1000 converted to 0-1 if necessary).
    """
    import re
    # Match <box>(x1, y1), (x2, y2)</box> or [x1, y1, x2, y2]
    # Qwen-VL usually uses <box>(x1,y1),(x2,y2)</box> normalized to 1000
    pattern = r'<box>\s*\((\d+),\s*(\d+)\),\s*\((\d+),\s*(\d+)\)\s*</box>'
    match = re.search(pattern, text)
    if not match:
        # Try simplified bracket format
        pattern_alt = r'\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]'
        match = re.search(pattern_alt, text)
        
    if match:
        coords = [int(g) for g in match.groups()]
        # Determine if normalized to 1000 or 1
        scale = 1000.0 if max(coords) > 1.1 else 1.0
        return {
            'x_min': coords[0] / scale,
            'y_min': coords[1] / scale,
            'x_max': coords[2] / scale,
            'y_max': coords[3] / scale
        }
    return None

def calculate_angle(x_min, x_max, hfov=90):
    """
    Calculates the horizontal angle relative to center (0.5).
    Formula: Angle = (X_center - 0.5) * HFOV
    """
    x_center = (x_min + x_max) / 2.0
    angle = (x_center - 0.5) * hfov
    return angle

def get_angle_range_label(angle):
    """
    Determines which range the angle falls into based on the -40 to +40 grid.
    """
    grid_points = [-40, -30, -20, -10, 0, 10, 20, 30, 40]
    
    if angle <= grid_points[0]:
        return f"Less than {grid_points[0]}°"
    if angle >= grid_points[-1]:
        return f"Greater than {grid_points[-1]}°"
    
    for i in range(len(grid_points) - 1):
        if grid_points[i] <= angle < grid_points[i+1]:
            return f"{grid_points[i]}° to {grid_points[i+1]}°"
    
    return "Unknown Range"


# --- OptiSight CoT Navigator Integration ---
autonomous_navigator = None

async def do_inference_for_navigator(prompt, device_choice, model_choice):
    global habitat_controller, model, processor, autonomous_navigator, grounded_sam
    
    # 1. Capture current frame and decode once for any mode
    frame_b64 = habitat_controller.get_frame_as_base64()
    import base64
    image_data = base64.b64decode(frame_b64)
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    
    # --- NEW: HIGH-SPEED SAM-ONLY MODE BYPASS ---
    # Used for fast retries in FINDING state without VLM overhead
    # Synchronized with manual mode by using the full run_grounded_sam logic
    if prompt == "[SAM_ONLY]":
        detections, final_response, angle_info = await run_grounded_sam(image, device_choice)
        
        if detections is not None and len(detections.xyxy) > 0:
            box = angle_info['box']
            box_str = f"<box>({box['x_min']:.3f},{box['y_min']:.3f}),({box['x_max']:.3f},{box['y_max']:.3f})</box>"
            return f"{final_response}\nGoal_Check: YES\n{box_str}"
        
        return f"{final_response}\nGoal_Check: NO"
    
    # --- GROUNDED-SAM BYPASS FOR AUTONOMOUS NAVIGATOR ---
    if autonomous_navigator and autonomous_navigator.state == "FINDING":
        # Only bypass if not explicitly using Bounding Box VLM mode
        if "bounding box" not in prompt.lower() and "<box>" not in prompt.lower():
            if grounded_sam is None and GroundedSAM is not None:
                logger.info("Initializing Grounded-SAM for Autonomous Navigator...")
                grounded_sam = GroundedSAM(device=device_choice)
            
            if grounded_sam:
                detections = grounded_sam.predict(image, text_prompt="door threshold, door frame, doorway, open door")
                if len(detections.xyxy) > 0:
                    best_idx = np.argmax(detections.confidence)
                    conf = detections.confidence[best_idx]
                    box = detections.xyxy[best_idx] # [x1, y1, x2, y2] in pixels
                    
                    # Normalize box for the navigator (0-1)
                    w, h = image.size
                    norm_box = [
                        float(box[0] / w),
                        float(box[1] / h),
                        float(box[2] / w),
                        float(box[3] / h)
                    ]
                    
                    logger.info(f"Autonomous Navigator: Grounded-SAM found door threshold ({conf:.2f}) at {norm_box}")
                    
                    # Generate sam_output.jpg for visual record in autonomous mode
                    try:
                        import cv2
                        image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                        mask_annotator = sv.MaskAnnotator()
                        box_annotator = sv.BoxAnnotator()
                        best_detection = detections[best_idx : best_idx + 1]
                        annotated_frame = mask_annotator.annotate(scene=image_cv.copy(), detections=best_detection)
                        annotated_frame = box_annotator.annotate(scene=annotated_frame, detections=best_detection)
                        cv2.imwrite("sam_output.jpg", annotated_frame)
                    except Exception as e:
                        logger.error(f"Failed to generate sam_output.jpg (Auto): {e}")

                    # Return a structured response that the navigator can parse
                    # Change Goal_Check to SPOTTED to avoid automatic transition to VISUAL_LOCK
                    box_str = f"<box>({norm_box[0]:.3f},{norm_box[1]:.3f}),({norm_box[2]:.3f},{norm_box[3]:.3f})</box>"
                    return f"Observation: Door threshold detected with {conf:.2f} confidence via Grounded-SAM specialized pipeline.\nGoal_Check: SPOTTED\nPlan: Awaiting operator confirmation or further alignment.\nReasoning: Precise detection achieved. Bounding box visible.\n{box_str}\n<cmd>Go Ahead</cmd>"

    # BURN THE GRID into the frame for Autonomous mode if NOT in Bounding Box mode
    # We use a flag or assume if BBox logic is used, grid is disabled.
    # For now, let's check a global state or pass it.
    # Since we don't have a direct flag here yet, I'll add a check for the prompt.
    if "bounding box" not in prompt.lower() and "<box>" not in prompt.lower():
        image = apply_angle_grid(image)
    else:
        logger.info("Skipping Angle Grid overlay for Bounding Box detection.")
    
    await load_model_on_demand(device_choice, model_choice)
    
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
        try:
            resp = requests.post("http://127.0.0.1:8001/analyze", json=api_payload, timeout=120)
            resp.raise_for_status()
            result_data = resp.json()
        except Exception as e:
            logger.error(f"Bridge Server Error: {e}")
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            raise Exception(f"VLM Bridge Server is currently unavailable or busy. Details: {str(e)}")
            
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            
        if result_data.get("status") == "success":
            return result_data.get("response")
        else:
            raise Exception(f"Bridge Model Error: {result_data.get('message')}")
            
async def do_move_for_navigator(action, bbox=None):
    global habitat_controller, autonomous_navigator
    if habitat_controller:
        async with habitat_lock:
            if action == "start_3d" and bbox:
                habitat_controller.start_3d_projection(bbox)
                frame = habitat_controller.get_frame_as_base64()
            elif action == "clear_3d":
                habitat_controller.tracked_3d_points = []
                habitat_controller.detected_obstacles_3d = []
                habitat_controller.planned_waypoints = []
                habitat_controller.logical_waypoints = []
                frame = habitat_controller.get_frame_as_base64()
            elif action == "plan_direct_path":
                habitat_controller.plan_path_with_sam_masks([])
                frame = habitat_controller.get_frame_as_base64()
                # We will fetch projection_info below
            elif action == "analyze_floor":
                # 1. Get current color sensor frame
                frame_b64 = habitat_controller.get_frame_as_base64()
                import io, base64
                from PIL import Image
                img_data = base64.b64decode(frame_b64)
                image = Image.open(io.BytesIO(img_data)).convert("RGB")
                
                # 2. Run Grounded-SAM on full visual frame (no crop!)
                logger.info("Running Grounded-SAM on full frame for floor scan...")
                detections, final_response, angle_info = await run_grounded_sam(
                    image, 
                    device_choice="cuda", 
                    text_prompt="bed, chair, table, box, furniture, obstacle",
                    scan_type="obstacle"
                )
                
                # 3. Process detections and project obstacles using SAM segmentation masks
                obstacle_masks = []
                if detections is not None and len(detections.xyxy) > 0:
                    for i in range(len(detections.xyxy)):
                        conf = detections.confidence[i]
                        if conf > 0.25: # Confidence threshold
                            if detections.mask is not None:
                                obstacle_masks.append(detections.mask[i])
                            else:
                                # Fallback to box mask if SAM mask is not available
                                h, w = image.height, image.width
                                box = detections.xyxy[i]
                                mask = np.zeros((h, w), dtype=bool)
                                u_min = max(0, int(box[0]))
                                v_min = max(0, int(box[1]))
                                u_max = min(w - 1, int(box[2]))
                                v_max = min(h - 1, int(box[3]))
                                if u_min < u_max and v_min < v_max:
                                    mask[v_min:v_max, u_min:u_max] = True
                                obstacle_masks.append(mask)
                            
                logger.info(f"Scanning complete. Found {len(obstacle_masks)} SAM masks.")
                
                # 4. Project boxes and plan path in habitat_controller using SAM masks
                obstacle_info = habitat_controller.plan_path_with_sam_masks(obstacle_masks)
                
                return {
                    "frame": habitat_controller.get_frame_as_base64(),
                    "obstacle_info": obstacle_info,
                    "projection_info": habitat_controller.get_projected_3d_points(), # Include projection update!
                    "waypoints_3d": [[float(coord) for coord in pt] for pt in getattr(habitat_controller, 'planned_waypoints', [])],
                    "obstacles_3d": [[[float(coord) for coord in pt] for pt in obs] for obs in getattr(habitat_controller, 'detected_obstacles_3d', [])],
                    "agent_pos": [float(c) for c in habitat_controller.agent.get_state().position]
                }
            elif action == "pop_waypoint":
                if hasattr(habitat_controller, 'planned_waypoints') and len(habitat_controller.planned_waypoints) > 0:
                    habitat_controller.planned_waypoints.pop(0)
                frame = habitat_controller.get_frame_as_base64()
            else:
                prev_collisions = habitat_controller.collision_count
                frame = habitat_controller.move_agent(action)
                # Check if a collision occurred during this move
                if habitat_controller.collision_count > prev_collisions:
                    if autonomous_navigator:
                        autonomous_navigator.trigger_collision()
            
            # Include projection info for real-time 3D persistence and navigation
            projection_info = habitat_controller.get_projected_3d_points()
            return {
                "frame": frame,
                "projection_info": projection_info,
                "collisions": habitat_controller.collision_count,
                "waypoints_3d": [[float(coord) for coord in pt] for pt in getattr(habitat_controller, 'planned_waypoints', [])],
                "obstacles_3d": [[[float(coord) for coord in pt] for pt in obs] for obs in getattr(habitat_controller, 'detected_obstacles_3d', [])],
                "agent_pos": [float(c) for c in habitat_controller.agent.get_state().position]
            }
    return None

@app.post("/start_autonomous_navigate")
async def start_autonomous_navigate(
    goal: str = Form(...),
    core_prompt: str = Form(None),
    searching_prompt: str = Form(None),
    finding_prompt: str = Form(None),
    navigating_prompt: str = Form(None),
    stopping_prompt: str = Form(None),
    recovering_prompt: str = Form(None),
    device_choice: str = Form("cuda"),
    model_choice: str = Form("qwen2-2b"),
    execute_cmds: str = Form("true"),
    initial_state: str = Form("SEARCHING"),
    visualize: str = Form("true"),
    scenario: str = Form("scenario1")
):
    global autonomous_navigator, habitat_controller
    if habitat_controller is None:
        return {"status": "error", "message": "Simulator not initialized"}
        
    execute_cmds_bool = execute_cmds.lower() == "true"
    visualize_bool = visualize.lower() == "true"
        
    if autonomous_navigator:
        # Signal any existing stream to stop and wait for it to cleanup
        autonomous_navigator.set_running(False)
        await asyncio.sleep(1.0) # Increased delay to ensure old session cleans up

    if habitat_controller:
        # Reset collision count only if starting a fresh analysis (not starting in RECOVERING state)
        reset_col = (initial_state != "RECOVERING")
        habitat_controller.clear_memory(reset_collisions=reset_col) # This clears tracked_3d_points

    if autonomous_navigator is None:
        autonomous_navigator = AutonomousNavigator(
            inference_callback=lambda p: do_inference_for_navigator(p, device_choice, model_choice),
            move_callback=do_move_for_navigator,
            execute_cmds=execute_cmds_bool
        )
        
    autonomous_navigator.inference_callback = lambda p: do_inference_for_navigator(p, device_choice, model_choice)
    autonomous_navigator.execute_cmds = execute_cmds_bool
    autonomous_navigator.visualize = visualize_bool
    
    prompts = {
        "core": core_prompt,
        "searching": searching_prompt,
        "finding": finding_prompt,
        "navigating": navigating_prompt,
        "stopping": stopping_prompt,
        "recovering": recovering_prompt
    }
    # Filter out None
    prompts = {k: v for k, v in prompts.items() if v is not None}
    
    autonomous_navigator.update_settings(goal, prompts=prompts, initial_state=initial_state, scenario=scenario)
    
    return {"status": "success"}

@app.get("/autonomous_navigate_stream")
async def autonomous_navigate_stream():
    global autonomous_navigator
    if autonomous_navigator is None:
        return {"status": "error", "message": "Not started"}
    return StreamingResponse(autonomous_navigator.navigate_stream(), media_type="text/event-stream")
    
@app.post("/stop_autonomous_navigate")
async def stop_autonomous_navigate():
    global autonomous_navigator, habitat_controller
    if autonomous_navigator:
        autonomous_navigator.set_running(False)
    if habitat_controller:
        habitat_controller.clear_memory(reset_collisions=True, keep_drawings=True)
    return {"status": "success"}

@app.post("/toggle_pause_autonav")
async def toggle_pause_autonav():
    global autonomous_navigator
    if autonomous_navigator is None:
        return {"status": "error", "message": "Navigator not initialized"}
    new_paused = not getattr(autonomous_navigator, "_is_paused", False)
    autonomous_navigator._is_paused = new_paused
    logger.info(f"Autonomous navigation paused status toggled to: {new_paused}")
    return {"status": "success", "is_paused": new_paused}

@app.post("/start_visual_servo")
async def start_visual_servo(
    x_min: float = Form(...),
    y_min: float = Form(...),
    x_max: float = Form(...),
    y_max: float = Form(...),
    visualize: str = Form("true")
):
    global autonomous_navigator, habitat_controller
    if habitat_controller is None:
        return {"status": "error", "message": "Simulator not initialized"}
    
    if autonomous_navigator is None:
        # We still need a dummy inference callback just in case, though pure visual servo won't use it
        autonomous_navigator = AutonomousNavigator(
            inference_callback=lambda p: "VISUAL_SERVO_MODE",
            move_callback=do_move_for_navigator,
            execute_cmds=True
        )
    
    autonomous_navigator.visualize = visualize.lower() == "true"
    bbox = [x_min, y_min, x_max, y_max]
    autonomous_navigator.start_visual_servo(bbox)
    
    return {"status": "success", "message": f"Visual servoing started with bbox {bbox}"}

@app.post("/save_experiment")
async def save_experiment(request: Request):
    try:
        data = await request.json()
        
        # Ensure experiments directory exists
        experiments_dir = os.path.join(os.getcwd(), "experiments")
        os.makedirs(experiments_dir, exist_ok=True)
        
        # Determine the next file number
        existing_files = [f for f in os.listdir(experiments_dir) if f.startswith("result_") and f.endswith(".txt")]
        next_num = 1
        if existing_files:
            numbers = []
            for f in existing_files:
                try:
                    num = int(f.replace("result_", "").replace(".txt", ""))
                    numbers.append(num)
                except ValueError:
                    continue
            if numbers:
                next_num = max(numbers) + 1
                
        filename = f"result_{next_num:02d}.txt"
        filepath = os.path.join(experiments_dir, filename)
        
        import textwrap
        from itertools import zip_longest

        # Format Metrics
        state_dist = data.get('stateDistribution', {})
        state_dist_str = f"S:{state_dist.get('SEARCHING',0)} F:{state_dist.get('FINDING',0)} N:{state_dist.get('NAVIGATING',0)} R:{state_dist.get('RECOVERING',0)} SC:{state_dist.get('SCANNING_PATH',0)}"

        metrics_lines = [
            "[ METRICS ]",
            "",
            f"Mission Success      : {data.get('missionSuccess', 'Unknown')}",
            f"Total Execution Time : {data.get('totalTime', '0')} s",
            f"Total Distance       : {data.get('totalDistance', '0.0')} m",
            f"Min Obstacle Dist    : {data.get('minObstacleDist', 'N/A')} m",
            f"Total Steps          : {data.get('steps', 0)}",
            f"Total Collisions     : {data.get('collisions', 0)}",
            f"Recoveries Triggered : {data.get('recoveries', 0)}",
            f"State Distribution   : {state_dist_str}",
            f"VLM Requests         : {data.get('vlmRequests', 0)}",
            f"Parse/Hallucinations : {data.get('parseErrors', 0)}"
        ]
        
        # Format Summary
        summary_raw = data.get("summary", [])
        summary_wrapped = []
        for line in summary_raw:
            wrapped = textwrap.wrap(line, width=55) # Wrap summary a bit tighter since we shifted right
            summary_wrapped.extend(wrapped)
            
        summary_lines = ["[ STEP-BY-STEP SUMMARY ]", ""] + summary_wrapped
        
        # Combine side by side
        left_width = 57 # Expanded for wider state distribution string
        combined_lines = []
        for left, right in zip_longest(metrics_lines, summary_lines, fillvalue=""):
            left_padded = left.ljust(left_width)
            combined_lines.append(f"{left_padded} | {right}")
            
        combined_text = "\n".join(combined_lines)
        
        header_footer = "=" * 115
        title = "EXPERIMENT RESULT".center(115)
        
        content = f"{header_footer}\n{title}\n{header_footer}\n\n{combined_text}\n\n{header_footer}\n"
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
        return {"status": "success", "filename": filename}
    except Exception as e:
        logger.error(f"Failed to save experiment: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
