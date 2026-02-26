import os
from habitat_controller import HabitatController

SCENE = "test habitats/skokloster-castle.glb"
if os.path.exists(SCENE):
    controller = HabitatController(SCENE)
    
    # move forward many times to ensure a collision
    collided = False
    for i in range(50):
        controller.move_agent("move_forward")
        if hasattr(controller.sim, 'previous_step_collided'):
            if controller.sim.previous_step_collided:
                collided = True
                print(f"Collided at step {i}")
                break
    
    if collided:
        print("previous_step_collided is available and works!")
    else:
        print("Did not detect collision using previous_step_collided. Attributes on sim:")
        print(dir(controller.sim))
else:
    print(f"Scene not found at {SCENE}")
