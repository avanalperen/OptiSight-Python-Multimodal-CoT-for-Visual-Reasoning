import os
import sys
import torch

# Ensure paths are absolute by resolving them against the project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Model Path Configuration ---

QWEN_PATH = os.path.join(BASE_DIR, "models", "Vision Language", "Qwen2-VL-2B")
QWEN35_08B_PATH = os.path.join(BASE_DIR, "models", "Vision Language", "Qwen3.5-VL-0.8B")
QWEN35_2B_PATH = os.path.join(BASE_DIR, "models", "Vision Language", "Qwen3.5-VL-2B")
MOONDREAM_PATH = os.path.join(BASE_DIR, "models", "Vision Language", "Moondream2-VL-2B")
SAM2_PATH = os.path.join(BASE_DIR, "models", "Segmentation", "sam2.1-hiera-tiny")
GD_PATH = os.path.join(BASE_DIR, "models", "Vision Foundation", "GroundingDINO-main")

# Default Model path for initial load/fallback
MODEL_PATH = QWEN_PATH

# --- Scene Path Configuration ---
# Priority:
# 1. Environment Variable 'SCENE_PATH'
# 2. Local relative path (Portable)

DEFAULT_SCENE_REL = os.path.join("habitats", "skokloster-castle.glb")
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
