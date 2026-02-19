import os
import numpy as np
import habitat_sim
from habitat_sim.utils.common import d3_40_colors_rgb
import cv2
import base64
from PIL import Image
import io

class HabitatController:
    def __init__(self, scene_path, width=640, height=480):
        self.scene_path = scene_path
        self.width = width
        self.height = height
        
        # Configure Simulator
        self.sim_cfg = habitat_sim.SimulatorConfiguration()
        self.sim_cfg.scene_id = self.scene_path
        self.sim_cfg.enable_physics = True
        
        # Configure Agent
        self.agent_cfg = habitat_sim.agent.AgentConfiguration()
        self.agent_cfg.sensor_specifications = [
            habitat_sim.CameraSensorSpec()
        ]
        self.agent_cfg.sensor_specifications[0].uuid = "color_sensor"
        self.agent_cfg.sensor_specifications[0].sensor_type = habitat_sim.SensorType.COLOR
        self.agent_cfg.sensor_specifications[0].resolution = [self.height, self.width]
        self.agent_cfg.sensor_specifications[0].position = [0.0, 1.5, 0.0]
        
        # Combine into a single Configuration object
        self.cfg = habitat_sim.Configuration(self.sim_cfg, [self.agent_cfg])
        
        # Initialize Simulator
        self.sim = habitat_sim.Simulator(self.cfg)
        self.agent = self.sim.initialize_agent(0)
        
        # Initial Agent State
        self.reset_agent()

    def reset_agent(self):
        agent_state = habitat_sim.AgentState()
        # Find a navigable point
        navigable_point = self.sim.pathfinder.get_random_navigable_point()
        agent_state.position = navigable_point
        self.agent.set_state(agent_state)

    def move_agent(self, action):
        """
        Action can be: 'move_forward', 'turn_left', 'turn_right'
        """
        if action == "move_forward":
            self.agent.act("move_forward")
        elif action == "move_backward":
            self.agent.act("move_backward")
        elif action == "turn_left":
            self.agent.act("turn_left")
        elif action == "turn_right":
            self.agent.act("turn_right")
        elif action == "look_up":
            self.agent.act("look_up")
        elif action == "look_down":
            self.agent.act("look_down")
        
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
