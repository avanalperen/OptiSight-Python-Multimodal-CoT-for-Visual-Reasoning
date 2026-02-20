
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath("/home/aavan/Desktop/Project Files/My Python Project/Project"))

try:
    from habitat_controller import HabitatController
    print("HabitatController imported successfully.")
except ImportError as e:
    print(f"Failed to import HabitatController: {e}")
    sys.exit(1)

scene_path = "test habitats/apartment_1.glb"
if not os.path.exists(scene_path):
    print(f"Scene not found: {scene_path}")
    sys.exit(1)

try:
    print(f"Initializing HabitatController with {scene_path}...")
    controller = HabitatController(scene_path)
    print("Controller initialized.")
    
    print("Getting initial frame...")
    frame = controller.get_frame_as_base64()
    print(f"Initial frame length detected: {len(frame)}")
    
    print("Moving agent...")
    frame = controller.move_agent("move_forward")
    print(f"Move frame length detected: {len(frame)}")

except Exception as e:
    print(f"Exception checking habitat: {e}")
