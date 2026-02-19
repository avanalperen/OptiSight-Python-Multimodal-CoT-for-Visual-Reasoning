import os
import sys
import torch

# Determine the base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Model Path Configuration ---
# Priority:
# 1. Environment Variable 'MODEL_PATH'
# 2. Local 'models' directory (Portable structure)
# 3. Legacy absolute path (Current user setup)

DEFAULT_MODEL_NAME = "qwen2-vl-2b"
LOCAL_MODEL_PATH = os.path.join(BASE_DIR, "models", DEFAULT_MODEL_NAME)
LEGACY_MODEL_PATH = "/home/aavan/Desktop/Project Files/Vision Language Models/qwen2-vl-2b"

if os.environ.get("MODEL_PATH"):
    MODEL_PATH = os.environ.get("MODEL_PATH")
elif os.path.exists(LOCAL_MODEL_PATH):
    MODEL_PATH = LOCAL_MODEL_PATH
elif os.path.exists(LEGACY_MODEL_PATH):
    MODEL_PATH = LEGACY_MODEL_PATH
else:
    # Default to local path (user needs to creating it)
    MODEL_PATH = LOCAL_MODEL_PATH

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
