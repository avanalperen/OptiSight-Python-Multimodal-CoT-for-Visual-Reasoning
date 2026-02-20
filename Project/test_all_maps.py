
import os
import sys

sys.path.append(os.path.abspath("/home/aavan/Desktop/Project Files/My Python Project/Project"))

try:
    from habitat_controller import HabitatController
    import habitat_sim
except ImportError as e:
    print(f"Failed to import: {e}")
    sys.exit(1)

maps = [
    "test habitats/apartment_1.glb",
    "test habitats/skokloster-castle.glb",
    "test habitats/van-gogh-room.glb"
]

for map_file in maps:
    print(f"\n--- Testing Map: {map_file} ---")
    if not os.path.exists(map_file):
        print(f"FAIL: Map file not found: {map_file}")
        continue

    try:
        print(f"Initializing controller...")
        controller = HabitatController(map_file)
        
        # Verify resolution
        res = controller.agent_cfg.sensor_specifications[0].resolution
        far = controller.agent_cfg.sensor_specifications[0].far
        print(f"Resolution: {res} (Expected: [720, 1280])")
        print(f"Far Plane: {far} (Expected: 1000.0)")
        
        if res != [720, 1280]:
            print("FAIL: Incorrect resolution.")
        elif far != 1000.0:
            print("FAIL: Incorrect far plane.")
        else:
            print("PASS: Configuration correct.")
            
        print("Capturing frame...")
        frame = controller.get_frame_as_base64()
        if len(frame) > 0:
            print(f"PASS: Frame captured. Size: {len(frame)}")
        else:
            print("FAIL: Empty frame.")
            
        controller.sim.close()
        del controller

    except Exception as e:
        print(f"FAIL: Exception: {e}")
