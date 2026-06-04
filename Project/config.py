import os
import sys
import torch

# Determine the base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Model Path Configuration ---

QWEN_PATH = "/mnt/c/Alperen/IRI Internship/Vision Language Models/qwen2-vl-2b"
QWEN35_08B_PATH = "/mnt/c/Alperen/IRI Internship/Vision Language Models/Qwen3.5-VL-0.8B"
QWEN35_2B_PATH = "/mnt/c/Alperen/IRI Internship/Vision Language Models/Qwen3.5-VL-2B"
SAM2_PATH = "/mnt/c/Alperen/IRI Internship/Vision Foundation Models/sam2.1-hiera-tiny"

# Default Model path for initial load/fallback
MODEL_PATH = QWEN_PATH

# --- Scene Path Configuration ---
# Priority:
# 1. Environment Variable 'SCENE_PATH'
# 2. Local relative path (Portable)

DEFAULT_SCENE_REL = os.path.join("test habitats", "skokloster-castle.glb")
LOCAL_SCENE_PATH = os.path.join(BASE_DIR, DEFAULT_SCENE_REL)

if os.environ.get("SCENE_PATH"):
    SCENE_PATH = os.environ.get("SCENE_PATH")
else:
    SCENE_PATH = LOCAL_SCENE_PATH

# --- Device Configuration ---
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# --- Habitat Sim Availability ---
HABITAT_AVAILABLE = False
try:
    import habitat_sim
    HABITAT_AVAILABLE = True
except (ImportError, ModuleNotFoundError, OSError):
    HABITAT_AVAILABLE = False

# --- Debug Info ---
if __name__ == "__main__":
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"MODEL_PATH: {MODEL_PATH}")
    print(f"SCENE_PATH: {SCENE_PATH}")
    print(f"DEVICE: {DEVICE}")
    print(f"HABITAT_AVAILABLE: {HABITAT_AVAILABLE}")
