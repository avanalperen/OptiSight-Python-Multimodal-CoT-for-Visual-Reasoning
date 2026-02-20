import os
import numpy as np
import habitat_sim
from habitat.utils.visualizations import maps
from habitat_sim.utils import common as utils_common
import numpy as np
import cv2
import base64
from PIL import Image
import io

class HabitatController:
    def __init__(self, scene_path, width=1920, height=1080, dataset_config=None, enable_physics=True):
        self.scene_path = scene_path
        self.width = width
        self.height = height
        
        # Configure Simulator
        self.sim_cfg = habitat_sim.SimulatorConfiguration()
        if dataset_config:
            self.sim_cfg.scene_dataset_config_file = dataset_config
        self.sim_cfg.scene_id = self.scene_path

        self.sim_cfg.enable_physics = enable_physics


        
        # Configure Agent
        self.agent_cfg = habitat_sim.agent.AgentConfiguration()
        self.agent_cfg.sensor_specifications = [
            habitat_sim.CameraSensorSpec()
        ]
        self.agent_cfg.sensor_specifications[0].uuid = "color_sensor"
        self.agent_cfg.sensor_specifications[0].sensor_type = habitat_sim.SensorType.COLOR
        self.agent_cfg.sensor_specifications[0].resolution = [self.height, self.width]
        self.agent_cfg.sensor_specifications[0].position = [0.0, 1.5, 0.0]
        self.agent_cfg.sensor_specifications[0].far = 1000.0 # Fix black areas in far distance

        # Define custom action space
        self.agent_cfg.action_space = {
            "move_forward": habitat_sim.agent.ActionSpec(
                "move_forward", habitat_sim.agent.ActuationSpec(amount=0.25)
            ),
            "move_backward": habitat_sim.agent.ActionSpec(
                "move_backward", habitat_sim.agent.ActuationSpec(amount=0.25)
            ),
            "turn_left": habitat_sim.agent.ActionSpec(
                "turn_left", habitat_sim.agent.ActuationSpec(amount=10.0)
            ),
            "turn_right": habitat_sim.agent.ActionSpec(
                "turn_right", habitat_sim.agent.ActuationSpec(amount=10.0)
            ),
            "look_up": habitat_sim.agent.ActionSpec(
                "look_up", habitat_sim.agent.ActuationSpec(amount=10.0)
            ),
            "look_down": habitat_sim.agent.ActionSpec(
                "look_down", habitat_sim.agent.ActuationSpec(amount=10.0)
            ),
            "turn_left_30": habitat_sim.agent.ActionSpec(
                "turn_left", habitat_sim.agent.ActuationSpec(amount=30.0)
            ),
            "turn_right_30": habitat_sim.agent.ActionSpec(
                "turn_right", habitat_sim.agent.ActuationSpec(amount=30.0)
            ),
            "look_up_30": habitat_sim.agent.ActionSpec(
                "look_up", habitat_sim.agent.ActuationSpec(amount=30.0)
            ),
            "look_down_30": habitat_sim.agent.ActionSpec(
                "look_down", habitat_sim.agent.ActuationSpec(amount=30.0)
            ),
        }
        
        # Combine into a single Configuration object
        self.cfg = habitat_sim.Configuration(self.sim_cfg, [self.agent_cfg])
        
        # Initialize Simulator
        self.sim = habitat_sim.Simulator(self.cfg)
        
        # Recompute NavMesh for HSSD scenes to enable pathfinding and collision
        print("Recomputing NavMesh...")
        nav_settings = habitat_sim.NavMeshSettings()
        nav_settings.set_defaults()
        nav_settings.include_static_objects = True
        if self.sim.recompute_navmesh(self.sim.pathfinder, nav_settings):
            print("NavMesh recomputed successfully.")
        else:
            print("Failed to recompute NavMesh.")

        self.agent = self.sim.initialize_agent(0)
        
        # Initial Agent State
        self.reset_agent()

    def reset_camera(self):
        """Resets the agent's rotation to default forward view."""
        state = self.agent.get_state()
        # Identity rotation (looking forward, level)
        state.rotation = np.array([0, 0, 0, 1.0]) # [x, y, z, w]
        self.agent.set_state(state)
        return self.get_frame_as_base64()

    def snap_to_floor(self):
        """Snaps the agent to the nearest navigable point on the floor."""
        state = self.agent.get_state()
        if self.sim.pathfinder.is_loaded:
            snapped = self.sim.pathfinder.snap_point(state.position)
            if not np.isnan(snapped).any():
                state.position = snapped
                self.agent.set_state(state)
        return self.get_frame_as_base64()

    def reset_agent(self):
        agent_state = habitat_sim.AgentState()
        try:
            # Try to find a navigable point
            if self.sim.pathfinder.is_loaded:
                navigable_point = self.sim.pathfinder.get_random_navigable_point()
                agent_state.position = navigable_point
            else:
                raise Exception("Pathfinder not loaded")
        except Exception as e:
            print(f"Warning: Failed to find navigable point ({e}). Using default position.")
            # Fallback for HSSD scenes without NavMesh
            agent_state.position = np.array([0.0, 1.0, 0.0]) 
            
        self.agent.set_state(agent_state)


    def move_agent(self, action):
        """
        Action can be: 'move_forward', 'move_backward', 'turn_left', 'turn_right', 'look_up', 'look_down'
        and 30-degree variations: 'turn_left_30', 'turn_right_30', 'look_up_30', 'look_down_30'
        """
        valid_actions = [
            "move_forward", "move_backward", 
            "turn_left", "turn_right", 
            "look_up", "look_down",
            "turn_left_30", "turn_right_30",
            "look_up_30", "look_down_30"
        ]
        
        if action in valid_actions:
            self.agent.act(action)
        elif action == "interact":
            # Simple interaction stub
            print("Interact action triggered")
            # Potential logic: Raycast forward, find object, toggle state
            # For now, just print to console.
        
        return self.get_frame_as_base64()

    def get_frame_as_base64(self):
        obs = self.sim.get_sensor_observations()
        rgb = obs["color_sensor"]
        
        # Convert to BGR for OpenCV
        rgb_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGBA2BGR)
        
        # Encode to JPEG
        _, buffer = cv2.imencode('.jpg', rgb_bgr)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        
        return jpg_as_text

    def generate_route_video(self, points=None, video_filename="route_video.mp4"):
        # points: List of 3D coordinates [x, y, z]
        
        path = habitat_sim.ShortestPath()
        
        if points and len(points) >= 2:
            path.requested_start = points[0]
            path.requested_end = points[-1]
        else:
            path.requested_start = self.sim.pathfinder.get_random_navigable_point()
            path.requested_end = self.sim.pathfinder.get_random_navigable_point()
        
        found_path = self.sim.pathfinder.find_path(path)
        found_path = self.sim.pathfinder.find_path(path)
        
        if not found_path:
            return False, "Path not found"
        
        # Prepare Video Writer
        os.makedirs(os.path.dirname(video_filename), exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(video_filename, fourcc, 10.0, (self.width, self.height))
        
        # Iterate through path points
        for point in path.points:
            # Move agent to point (simplistic jump for now, can interpolate for smooth transition)
            state = self.agent.get_state()
            state.position = point
            self.agent.set_state(state)
            
            # Capture Frame
            obs = self.sim.get_sensor_observations()
            rgb = obs["color_sensor"]
            rgb_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGBA2BGR)
            video.write(rgb_bgr)
            
        video.release()
        return True, video_filename

    def get_topdown_map_base64(self):
        """Generates a topdown map of the environment."""
        if not self.sim.pathfinder.is_loaded:
            return None, "Pathfinder not loaded"

        try:
            # Get bounds
            bounds = self.sim.pathfinder.get_bounds()
            # Calculate height (mid point of bounds y) or just slightly above min
            # Usually we want a slice at agent height or floor
            # Let's use lower_bound.y + 1.0 meter
            height = bounds[0][1] + 1.0
            
            meters_per_pixel = 0.05 # 5cm resolution
            
            # Generate map
            topdown_map = maps.get_topdown_map(
                self.sim.pathfinder, 
                height=height, 
                meters_per_pixel=meters_per_pixel
            )
            
            # Reproject to image (0=obstacle, 1=navigable?)
            # Usually: 0 -> obstacle, 1 -> free
            # Let's map 1 to White, 0 to Black
            color_map = np.zeros((topdown_map.shape[0], topdown_map.shape[1], 3), dtype=np.uint8)
            color_map[topdown_map > 0] = [255, 255, 255] # Walkable areas white
            
            # Draw current agent position
            agent_pos = self.agent.get_state().position
            grid_loc = maps.to_grid(
                agent_pos[0], 
                agent_pos[2], 
                (topdown_map.shape[0], topdown_map.shape[1]), 
                pathfinder=self.sim.pathfinder
            )
            
            # Draw red circle for agent
            # Note: cv2 uses (x,y) = (col, row), to_grid returns (row, col) usually? 
            # maps.to_grid returns (row, col). So flip for cv2.
            cv2.circle(color_map, (grid_loc[1], grid_loc[0]), 5, (0, 0, 255), -1)

            # Encode
            _, buffer = cv2.imencode('.jpg', color_map)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            
            return jpg_as_text, {
                "width": topdown_map.shape[1],
                "height": topdown_map.shape[0],
                "meters_per_pixel": meters_per_pixel,
                "bound_min": [float(bounds[0][0]), float(bounds[0][1]), float(bounds[0][2])],
                "bound_max": [float(bounds[1][0]), float(bounds[1][1]), float(bounds[1][2])]
            }

        except Exception as e:
            return None, str(e)

    def set_agent_start_pose(self, normalized_x, normalized_y, map_info):
        """
        Sets agent position based on normalized map coordinates (0.0 to 1.0).
        """
        try:
            height = map_info["height"] # Rows
            width = map_info["width"]   # Cols
            
            grid_r = int(normalized_y * height)
            grid_c = int(normalized_x * width)
            
            world_x, world_z = maps.from_grid(
                grid_r, 
                grid_c, 
                (height, width), 
                pathfinder=self.sim.pathfinder
            )
            
            # Try to snap near the floor
            bounds = self.sim.pathfinder.get_bounds()
            floor_y = bounds[0][1] + 0.1 # Slightly above floor min
            target_pos = np.array([world_x, floor_y, world_z])
            
            # Snap to nearest navigable point
            snapped_pos = self.sim.pathfinder.snap_point(target_pos)
            
            if np.isnan(snapped_pos).any():
                # Fallback to current agent height if floor snap fails
                current_y = self.agent.get_state().position[1]
                target_pos[1] = current_y
                snapped_pos = self.sim.pathfinder.snap_point(target_pos)

            if np.isnan(snapped_pos).any():
                return False, "Point is not navigable."
                
            agent_state = self.agent.get_state()
            agent_state.position = snapped_pos
            # Reset rotation to look forward when spawning
            agent_state.rotation = np.array([0, 0, 0, 1.0])
            self.agent.set_state(agent_state)
            
            return True, self.get_frame_as_base64()
            
        except Exception as e:
            return False, str(e)

if __name__ == "__main__":
    # Test Block
    SCENE = "test habitats/skokloster-castle.glb"
    if os.path.exists(SCENE):
        controller = HabitatController(SCENE)
        print("Simulator Initialized")
        frame = controller.move_agent("move_forward")
        print(f"Captured frame (base64 length: {len(frame)})")
        
        success, vid_path = controller.generate_route_video(video_filename="static/test_videos/test_route.mp4")
        if success:
            print(f"Video generated: {vid_path}")
        else:
            print(f"Video generation failed: {vid_path}")
    else:
        print(f"Scene not found at {SCENE}")
