
import habitat_sim
from habitat.utils.visualizations import maps
import numpy as np
import cv2
import os

# Config
dataset_config = "/home/aavan/Desktop/Project Files/AIHabitat Project/Hssd Habitat Dataset/hssd/hssd-hab.scene_dataset_config.json"
scene_id = "102343992" 

# Init Sim
sim_cfg = habitat_sim.SimulatorConfiguration()
sim_cfg.scene_dataset_config_file = dataset_config
sim_cfg.scene_id = scene_id
sim_cfg.enable_physics = True

agent_cfg = habitat_sim.agent.AgentConfiguration()
cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
sim = habitat_sim.Simulator(cfg)

# Recompute NavMesh (required for map)
print("Recomputing NavMesh...")
nav_settings = habitat_sim.NavMeshSettings()
nav_settings.set_defaults()
nav_settings.include_static_objects = True
sim.recompute_navmesh(sim.pathfinder, nav_settings)

# Generate Map
print("Generating TopDown Map...")
# height usually 0 or center of scene?
# We can use pathfinder bounds
bounds = sim.pathfinder.get_bounds()
lower_bound = bounds[0]
upper_bound = bounds[1]
meters_per_pixel = 0.05

print(f"Bounds: {lower_bound} to {upper_bound}")

# Taking the middle height
height = lower_bound[1] + 1.0 

topdown_map = maps.get_topdown_map(
    sim.pathfinder, 
    height=height, 
    meters_per_pixel=meters_per_pixel
)

# Ref: habitat_sim/utils/maps.py
# 0 = navigable, 1 = obstacle? No, it returns a grid.
# Actually habitat_sim.utils.maps.get_topdown_map output depends on implementation.
# Let's inspect unique values.
print(f"Map Shape: {topdown_map.shape}")
print(f"Unique values: {np.unique(topdown_map)}")

# Colorize
# 0: Occupied, 1: Free? Or habitat_sim maps usually:
# 1 is walkable, 0 is obstacle? Let's assume generic occupancy grid.
# Reproject to image
color_map = np.zeros((topdown_map.shape[0], topdown_map.shape[1], 3), dtype=np.uint8)
color_map[topdown_map == 1] = [255, 255, 255] # White for walkable
color_map[topdown_map == 0] = [0, 0, 0]       # Black for obstacle

# Save
cv2.imwrite("test_map.png", color_map)
print("Map saved to test_map.png")

# Coordinate Conversion Test
# Let's pick a random navigable point
pt = sim.pathfinder.get_random_navigable_point()
print(f"Random Point 3D: {pt}")

# Convert to Grid
# maps.to_grid(real_world_x, real_world_z, coordinate_min, grid_resolution)
# grid_resolution = (map_width, map_height) ? No.
# habitat_sim.utils.maps provides to_grid()
grid_x, grid_y = maps.to_grid(
    pt[0], 
    pt[2], 
    (topdown_map.shape[0], topdown_map.shape[1]), 
    pathfinder=sim.pathfinder
)
print(f"Projected Grid Point: ({grid_x}, {grid_y})")

# Draw point
cv2.circle(color_map, (grid_y, grid_x), 5, (0, 0, 255), -1) # Note: cv2 uses (x,y) which is (col, row)
cv2.imwrite("test_map_point.png", color_map)

# Convert BACK to World
# from_grid(grid_x, grid_y, coordinate_min, grid_resolution)
world_x, world_z = maps.from_grid(
    grid_x, 
    grid_y,
    (topdown_map.shape[0], topdown_map.shape[1]),
    pathfinder=sim.pathfinder
)
print(f"Recovered World Point: ({world_x}, {pt[1]}, {world_z})")

sim.close()
