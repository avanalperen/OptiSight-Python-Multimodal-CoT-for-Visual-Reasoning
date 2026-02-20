
import os
import sys

sys.path.append(os.path.abspath("/home/aavan/Desktop/Project Files/My Python Project/Project"))

try:
    from habitat_controller import HabitatController
    import habitat_sim
except ImportError as e:
    print(f"Failed to import: {e}")
    sys.exit(1)

if __name__ == "__main__":
    # HSSD Configuration
    # We point to the original dataset config to resolve object paths correctly
    dataset_config = "/home/aavan/Desktop/Project Files/AIHabitat Project/Hssd Habitat Dataset/hssd/hssd-hab.scene_dataset_config.json"
    
    # Scene Handle (ID from the file name, without extension)
    scene_id = "102343992" 
    
    print(f"\n--- Testing HSSD Scene Loading ---")
    print(f"Dataset Config: {dataset_config}")
    print(f"Scene ID: {scene_id}")

    if not os.path.exists(dataset_config):
         print(f"FAIL: Config file not found: {dataset_config}")
         sys.exit(1)

    try:
        print(f"Initializing HabitatController with dataset_config (Physics ENABLED)...")
        # We pass scene_id as scene_path, and provide dataset_config
        # Note: We need to modify HabitatController to allow enabling physics again.
        # For now, let's assume I will modify the class in the next tool call.
        controller = HabitatController(scene_id, dataset_config=dataset_config, enable_physics=True)
        
        print("Simulator initialized. Attempting to recompute NavMesh...")
        # Get pathfinder and settings
        nav_settings = habitat_sim.NavMeshSettings()
        nav_settings.set_defaults()
        nav_settings.include_static_objects = True
        
        success = controller.sim.recompute_navmesh(controller.sim.pathfinder, nav_settings)
        if success:
            print("PASS: NavMesh recomputed successfully.")
            if controller.sim.pathfinder.is_loaded:
                print("PASS: Pathfinder is now loaded.")
                # Test a random point
                try:
                    pt = controller.sim.pathfinder.get_random_navigable_point()
                    print(f"Random Nav Point: {pt}")
                except:
                    print("FAIL: Random point failed even after recompute.")
        else:
            print("FAIL: NavMesh recompute failed.")
        
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
