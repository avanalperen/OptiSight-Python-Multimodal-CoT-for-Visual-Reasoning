
import requests
import base64
import os
import sys

# Since we cannot easily start the full FastAPI server with uvicorn in a script and query it 
# without blocking or complex multiprocessing in this environment, 
# we will verify the habitat_controller.get_frame_as_base64() logic again 
# and trust the FastAPI wrapper (which is standard).
# 
# However, we can try to import the app and test the endpoint function directly if we mock the request.
# But habitat_controller needs to be initialized.

sys.path.append(os.path.abspath("/home/aavan/Desktop/Project Files/My Python Project/Project"))

try:
    from habitat_controller import HabitatController
    print("HabitatController imported.")
    
    scene_path = "test habitats/apartment_1.glb"
    if not os.path.exists(scene_path):
        print(f"Scene not found: {scene_path}")
        sys.exit(1)
        
    controller = HabitatController(scene_path)
    print("Controller initialized.")
    
    frame = controller.get_frame_as_base64()
    if frame and len(frame) > 0:
        print(f"PASS: Frame retrieved successfully. Length: {len(frame)}")
    else:
        print("FAIL: Frame is empty.")

except Exception as e:
    print(f"FAIL: Exception: {e}")
