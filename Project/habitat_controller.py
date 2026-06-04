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
from collections import deque
import re

# Allow software rendering or display fallback on WSL
os.environ["DISPLAY"] = ":0"
os.environ["MESA_GL_VERSION_OVERRIDE"] = "3.3"
os.environ["MESA_GLSL_VERSION_OVERRIDE"] = "330"

def draw_dashed_line(img, pt1, pt2, color, thickness=4, step=8, gap=8):
    """Draws a dashed line between pt1 and pt2 using OpenCV."""
    x1, y1 = pt1
    x2, y2 = pt2
    dist = np.hypot(x2 - x1, y2 - y1)
    if dist < 1e-5:
        return
    
    dx = (x2 - x1) / dist
    dy = (y2 - y1) / dist
    
    current_dist = 0
    draw = True
    while current_dist < dist:
        length = step if draw else gap
        if current_dist + length > dist:
            length = dist - current_dist
            
        next_dist = current_dist + length
        
        if draw:
            p_start = (int(x1 + current_dist * dx), int(y1 + current_dist * dy))
            p_end = (int(x1 + next_dist * dx), int(y1 + next_dist * dy))
            cv2.line(img, p_start, p_end, color, thickness)
            
        current_dist = next_dist
        draw = not draw


class HabitatController:
    def __init__(self, scene_path, width=1920, height=1080, dataset_config=None, enable_physics=True, hfov=90):
        self.scene_path = scene_path
        self.width = int(width)
        self.height = int(height)
        self.hfov = float(hfov)
        
        # OptiSight Memory System (Previous 2 commands + reasoning)
        self.memory = deque(maxlen=2)
        
        # Configure Simulator
        self.sim_cfg = habitat_sim.SimulatorConfiguration()
        if dataset_config:
            self.sim_cfg.scene_dataset_config_file = dataset_config
        self.sim_cfg.scene_id = self.scene_path

        self.sim_cfg.enable_physics = enable_physics
        self.sim_cfg.gpu_device_id = -1 # Force CPU for Simulator to bypass WSL Headless CUDA EGL issue
        self.sim_cfg.allow_sliding = True


        
        # Configure Agent
        self.agent_cfg = habitat_sim.agent.AgentConfiguration()
        self.agent_cfg.sensor_specifications = [
            habitat_sim.CameraSensorSpec(),
            habitat_sim.CameraSensorSpec()
        ]
        self.agent_cfg.sensor_specifications[0].uuid = "color_sensor"
        self.agent_cfg.sensor_specifications[0].sensor_type = habitat_sim.SensorType.COLOR
        self.agent_cfg.sensor_specifications[0].resolution = [self.height, self.width]
        self.agent_cfg.sensor_specifications[0].position = [0.0, 1.5, 0.0]
        self.agent_cfg.sensor_specifications[0].hfov = self.hfov
        self.agent_cfg.sensor_specifications[0].far = 1000.0 # Fix black areas in far distance

        self.agent_cfg.sensor_specifications[1].uuid = "depth_sensor"
        self.agent_cfg.sensor_specifications[1].sensor_type = habitat_sim.SensorType.DEPTH
        self.agent_cfg.sensor_specifications[1].resolution = [self.height, self.width]
        self.agent_cfg.sensor_specifications[1].position = [0.0, 1.5, 0.0]
        self.agent_cfg.sensor_specifications[1].hfov = self.hfov
        self.agent_cfg.sensor_specifications[1].far = 1000.0

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
            "turn_left_5": habitat_sim.agent.ActionSpec(
                "turn_left", habitat_sim.agent.ActuationSpec(amount=5.0)
            ),
            "turn_right_5": habitat_sim.agent.ActionSpec(
                "turn_right", habitat_sim.agent.ActuationSpec(amount=5.0)
            ),
            "look_up": habitat_sim.agent.ActionSpec(
                "look_up", habitat_sim.agent.ActuationSpec(amount=10.0)
            ),
            "look_down": habitat_sim.agent.ActionSpec(
                "look_down", habitat_sim.agent.ActuationSpec(amount=10.0)
            ),
            "look_up_30": habitat_sim.agent.ActionSpec(
                "look_up", habitat_sim.agent.ActuationSpec(amount=30.0)
            ),
            "look_down_30": habitat_sim.agent.ActionSpec(
                "look_down", habitat_sim.agent.ActuationSpec(amount=30.0)
            ),
            "turn_left_30": habitat_sim.agent.ActionSpec(
                "turn_left", habitat_sim.agent.ActuationSpec(amount=30.0)
            ),
            "turn_right_30": habitat_sim.agent.ActionSpec(
                "turn_right", habitat_sim.agent.ActuationSpec(amount=30.0)
            ),
            "turn_left_20": habitat_sim.agent.ActionSpec(
                "turn_left", habitat_sim.agent.ActuationSpec(amount=20.0)
            ),
            "turn_right_20": habitat_sim.agent.ActionSpec(
                "turn_right", habitat_sim.agent.ActuationSpec(amount=20.0)
            ),
            "turn_left_40": habitat_sim.agent.ActionSpec(
                "turn_left", habitat_sim.agent.ActuationSpec(amount=40.0)
            ),
            "turn_right_40": habitat_sim.agent.ActionSpec(
                "turn_right", habitat_sim.agent.ActuationSpec(amount=40.0)
            ),
            "look_up_40": habitat_sim.agent.ActionSpec(
                "look_up", habitat_sim.agent.ActuationSpec(amount=40.0)
            ),
            "look_down_40": habitat_sim.agent.ActionSpec(
                "look_down", habitat_sim.agent.ActuationSpec(amount=40.0)
            ),
            "turn_left_90": habitat_sim.agent.ActionSpec(
                "turn_left", habitat_sim.agent.ActuationSpec(amount=90.0)
            ),
            "turn_right_90": habitat_sim.agent.ActionSpec(
                "turn_right", habitat_sim.agent.ActuationSpec(amount=90.0)
            ),
            "move_forward_small": habitat_sim.agent.ActionSpec(
                "move_forward", habitat_sim.agent.ActuationSpec(amount=0.05)
            ),
            "move_backward_small": habitat_sim.agent.ActionSpec(
                "move_backward", habitat_sim.agent.ActuationSpec(amount=0.05)
            ),
            "turn_left_10": habitat_sim.agent.ActionSpec(
                "turn_left", habitat_sim.agent.ActuationSpec(amount=10.0)
            ),
            "turn_right_10": habitat_sim.agent.ActionSpec(
                "turn_right", habitat_sim.agent.ActuationSpec(amount=10.0)
            ),
            "turn_left_15": habitat_sim.agent.ActionSpec(
                "turn_left", habitat_sim.agent.ActuationSpec(amount=15.0)
            ),
            "turn_right_15": habitat_sim.agent.ActionSpec(
                "turn_right", habitat_sim.agent.ActuationSpec(amount=15.0)
            ),
            "refresh": habitat_sim.agent.ActionSpec(
                "move_forward", habitat_sim.agent.ActuationSpec(amount=0.00)
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
        
        self.collision_count = 0
        self.height_offset = 0.0
        self.tracked_3d_points = []
        self.detected_obstacles_3d = []
        self.planned_waypoints = []
        self.logical_waypoints = []
        self.accumulated_obstacle_points = []
        
        # Initial Agent State
        self.reset_agent()
        self.starter_position = self.agent.get_state().position
        self._apply_height_offset()

    def _apply_height_offset(self):
        """Internal helper to ensure camera height is correct relative to the agent."""
        clamped_offset = max(-1.2, min(1.0, self.height_offset))
        self.height_offset = clamped_offset
        for sensor_name in ["color_sensor", "depth_sensor"]:
            sensor_node = self.agent.scene_node.node_sensor_suite.get(sensor_name).node
            sensor_node.translation = np.array([0.0, 1.5 + clamped_offset, 0.0])
        # Force a simulation step with 0 movement to refresh the visual sensors
        self.agent.act("refresh")

    def start_3d_projection(self, bbox_normalized):
        """Calculates 3D world coordinates for the bounding box corners using depth map."""
        x_min, y_min, x_max, y_max = bbox_normalized
        
        # --- IMPROVEMENT: Box Inset ---
        # We shrink the box slightly (e.g. 5%) to ensure we sample points DEFINITELY inside the target.
        # This prevents picking up background depth or edge artifacts, especially when close.
        inset = 0.05
        w_box = x_max - x_min
        h_box = y_max - y_min
        x_min_in = x_min + w_box * inset
        x_max_in = x_max - w_box * inset
        y_min_in = y_min + h_box * inset
        y_max_in = y_max - h_box * inset
        
        obs = self.sim.get_sensor_observations()
        depth_img = obs.get("depth_sensor")
        if depth_img is None:
            return False
            
        h, w = depth_img.shape
        
        # Convert normalized to pixel coordinates using INSET boundaries
        p1 = [int(x_min_in * w), int(y_min_in * h)] # Top-Left
        p2 = [int(x_max_in * w), int(y_min_in * h)] # Top-Right
        p3 = [int(x_max_in * w), int(y_max_in * h)] # Bottom-Right
        p4 = [int(x_min_in * w), int(y_max_in * h)] # Bottom-Left
        
        # Ensure within bounds
        points_2d = []
        for p in [p1, p2, p3, p4]:
            px = min(max(p[0], 0), w-1)
            py = min(max(p[1], 0), h-1)
            points_2d.append((px, py))
            
        # Camera Intrinsics
        hfov_rad = np.deg2rad(self.hfov)
        fx = (w / 2.0) / np.tan(hfov_rad / 2.0)
        fy = fx
        cx, cy = w / 2.0, h / 2.0
        
        sensor_node = self.agent.scene_node.node_sensor_suite.get("color_sensor").node
        T_wc = np.array(sensor_node.absolute_transformation())
        
        self.tracked_3d_points = []
        for (u, v) in points_2d:
            # --- IMPROVEMENT: Patch-based Median Depth ---
            # Sampling a single pixel at the edge is risky. We take a 5x5 patch and use median.
            u_min, u_max = max(0, u-2), min(w-1, u+2)
            v_min, v_max = max(0, v-2), min(h-1, v+2)
            patch = depth_img[v_min:v_max+1, u_min:u_max+1]
            
            # Filter out extreme values (0 or too far/near)
            valid_patch = patch[(patch > 0.1) & (patch < 20.0)]
            if valid_patch.size > 0:
                d = float(np.median(valid_patch))
            else:
                d = float(depth_img[v, u]) if depth_img[v, u] > 0.1 else 1.0
            
            # Camera Local coordinates (Habitat: -Z forward, Y up, X right)
            x_c = (u - cx) * d / fx
            y_c = (cy - v) * d / fy 
            z_c = -d
            
            P_c = np.array([x_c, y_c, z_c, 1.0])
            P_w = T_wc @ P_c
            self.tracked_3d_points.append(P_w)
            
        return True

    def get_projected_3d_points(self):
        """Returns the 2D projected screen coordinates of the tracked 3D points, obstacles, and routes."""
        projected_corners = []
        if hasattr(self, 'tracked_3d_points') and self.tracked_3d_points:
            sensor_node = self.agent.scene_node.node_sensor_suite.get("color_sensor").node
            T_wc = np.array(sensor_node.absolute_transformation())
            T_cw = np.linalg.inv(T_wc)
            
            w, h = self.width, self.height
            hfov_rad = np.deg2rad(self.hfov)
            fx = (w / 2.0) / np.tan(hfov_rad / 2.0)
            fy = fx
            cx, cy = w / 2.0, h / 2.0
            
            for P_w in self.tracked_3d_points:
                P_c = T_cw @ P_w
                z_dist = -P_c[2]
                
                if z_dist > 1e-4: # Point is in front of camera
                    u = (P_c[0] * fx / z_dist) + cx
                    v = cy - (P_c[1] * fy / z_dist)
                    
                    projected_corners.append({
                        "x": float(u / w),
                        "y": float(v / h)
                    })
                else:
                    u = (P_c[0] * fx / 1e-4) + cx
                    v = cy - (P_c[1] * fy / 1e-4)
                    projected_corners.append({
                        "x": float(u / w),
                        "y": float(v / h),
                        "behind": True
                    })
                    
        # Project obstacles
        projected_obstacles = []
        for obs_points in self.detected_obstacles_3d:
            proj_obs = self.project_world_points_to_screen(obs_points)
            projected_obstacles.append(proj_obs)
            
        # Project planned waypoints
        projected_route = self.project_world_points_to_screen(self.planned_waypoints)
        
        # Project planned waypoints as a 3D ribbon (left and right side boundary lines)
        projected_ribbon_left = []
        projected_ribbon_right = []
        n = len(self.planned_waypoints)
        if n >= 2:
            half_width = 0.25  # 0.5m total width
            for i in range(n):
                pt = np.array(self.planned_waypoints[i])
                if i < n - 1:
                    direction = np.array(self.planned_waypoints[i+1]) - pt
                else:
                    direction = pt - np.array(self.planned_waypoints[i-1])
                direction[1] = 0.0  # Zero horizontal height differences
                norm = np.linalg.norm(direction)
                if norm > 1e-5:
                    dir_xz = direction / norm
                else:
                    dir_xz = np.array([1.0, 0.0, 0.0])
                
                # Orthogonal horizontal direction
                ortho = np.array([-dir_xz[2], 0.0, dir_xz[0]])
                
                pt_left = pt - half_width * ortho
                pt_right = pt + half_width * ortho
                
                proj_left = self.project_world_points_to_screen([pt_left.tolist()])[0]
                proj_right = self.project_world_points_to_screen([pt_right.tolist()])[0]
                
                projected_ribbon_left.append(proj_left)
                projected_ribbon_right.append(proj_right)
        elif n == 1:
            # Single waypoint fallback
            pt = np.array(self.planned_waypoints[0])
            ortho = np.array([1.0, 0.0, 0.0])
            pt_left = pt - 0.25 * ortho
            pt_right = pt + 0.25 * ortho
            proj_left = self.project_world_points_to_screen([pt_left.tolist()])[0]
            proj_right = self.project_world_points_to_screen([pt_right.tolist()])[0]
            projected_ribbon_left.append(proj_left)
            projected_ribbon_right.append(proj_right)
        
        # Project logical waypoints
        projected_logical = []
        if hasattr(self, 'logical_waypoints') and self.logical_waypoints:
            projected_logical = self.project_world_points_to_screen(self.logical_waypoints)
        
        return {
            "corners": projected_corners,
            "obstacles": projected_obstacles,
            "sam_masks": projected_obstacles,
            "route": projected_route,
            "route_left": projected_ribbon_left,
            "route_right": projected_ribbon_right,
            "logical_waypoints": projected_logical
        }

    def project_world_points_to_screen(self, points_3d):
        """Projects a list of 3D world coordinates [x, y, z] to 2D normalized screen coordinates."""
        if not points_3d:
            return []
            
        sensor_node = self.agent.scene_node.node_sensor_suite.get("color_sensor").node
        T_wc = np.array(sensor_node.absolute_transformation())
        T_cw = np.linalg.inv(T_wc)
        
        w, h = self.width, self.height
        hfov_rad = np.deg2rad(self.hfov)
        fx = (w / 2.0) / np.tan(hfov_rad / 2.0)
        fy = fx
        cx, cy = w / 2.0, h / 2.0
        
        projected = []
        for P_w in points_3d:
            if len(P_w) == 3:
                P_w_hom = np.array([P_w[0], P_w[1], P_w[2], 1.0])
            else:
                P_w_hom = np.array(P_w)
                
            P_c = T_cw @ P_w_hom
            z_dist = -P_c[2]
            
            if z_dist > 1e-4:
                u = (P_c[0] * fx / z_dist) + cx
                v = cy - (P_c[1] * fy / z_dist)
                projected.append({
                    "x": float(u / w),
                    "y": float(v / h),
                    "behind": False
                })
            else:
                u = (P_c[0] * fx / 1e-4) + cx
                v = cy - (P_c[1] * fy / 1e-4)
                projected.append({
                    "x": float(u / w),
                    "y": float(v / h),
                    "behind": True
                })
        return projected

    def project_bbox_to_3d_points(self, bbox_normalized):
        """Calculates 3D world coordinates for the corners of a bounding box using depth map."""
        x_min, y_min, x_max, y_max = bbox_normalized
        
        obs = self.sim.get_sensor_observations()
        depth_img = obs.get("depth_sensor")
        if depth_img is None:
            return []
            
        h, w = depth_img.shape
        
        # Convert normalized boundaries to pixel ranges
        u_min = max(0, int(x_min * w))
        u_max = min(w - 1, int(x_max * w))
        v_min = max(0, int(y_min * h))
        v_max = min(h - 1, int(y_max * h))
        
        if u_min >= u_max or v_min >= v_max:
            return []
            
        # Sample depths in a grid inside the bounding box
        u_coords = np.linspace(u_min, u_max, 15, dtype=int)
        v_coords = np.linspace(v_min, v_max, 15, dtype=int)
        
        # Get all depth values inside the box
        depth_samples = []
        for u in u_coords:
            for v in v_coords:
                d = float(depth_img[v, u])
                if 0.15 < d < 15.0: # Keep valid depth range
                    depth_samples.append(d)
                    
        if not depth_samples:
            return []
            
        # Use robust percentile to eliminate extreme outliers (background/foreground)
        d_min = float(np.percentile(depth_samples, 10))
        d_max = float(np.percentile(depth_samples, 90))
        
        # Camera Intrinsics
        hfov_rad = np.deg2rad(self.hfov)
        fx = (w / 2.0) / np.tan(hfov_rad / 2.0)
        fy = fx
        cx, cy = w / 2.0, h / 2.0
        
        sensor_node = self.agent.scene_node.node_sensor_suite.get("color_sensor").node
        T_wc = np.array(sensor_node.absolute_transformation())
        
        world_points = []
        for u in u_coords:
            for v in v_coords:
                d = float(depth_img[v, u])
                if d_min <= d <= d_max:
                    # Project pixel to 3D world coordinates
                    x_c = (u - cx) * d / fx
                    y_c = (cy - v) * d / fy
                    z_c = -d
                    P_c = np.array([x_c, y_c, z_c, 1.0])
                    P_w = T_wc @ P_c
                    world_points.append(P_w[:3])
                    
        if not world_points:
            return []
            
        world_points = np.array(world_points)
        
        # Calculate Axis-Aligned Bounding Box (AABB) in the world frame
        x_w_min, x_w_max = np.min(world_points[:, 0]), np.max(world_points[:, 0])
        y_w_min, y_w_max = np.min(world_points[:, 1]), np.max(world_points[:, 1])
        z_w_min, z_w_max = np.min(world_points[:, 2]), np.max(world_points[:, 2])
        
        # Apply a minimal padding (e.g. 5cm) to ensure the 3D box covers the object edges cleanly
        pad_x = 0.05
        pad_y = 0.05
        pad_z = 0.05
        
        x_w_min -= pad_x
        x_w_max += pad_x
        y_w_min -= pad_y
        y_w_max += pad_y
        z_w_min -= pad_z
        z_w_max += pad_z
        
        # 8 corners of the axis-aligned cuboid mapping to standard wireframe projection logic:
        # Bottom face (y = y_w_min)
        p0 = [x_w_min, y_w_min, z_w_min] # Bottom-Left-Front
        p1 = [x_w_max, y_w_min, z_w_min] # Bottom-Right-Front
        p2 = [x_w_min, y_w_min, z_w_max] # Bottom-Left-Back
        p3 = [x_w_max, y_w_min, z_w_max] # Bottom-Right-Back
        
        # Top face (y = y_w_max)
        p4 = [x_w_min, y_w_max, z_w_min] # Top-Left-Front
        p5 = [x_w_max, y_w_max, z_w_min] # Top-Right-Front
        p6 = [x_w_min, y_w_max, z_w_max] # Top-Left-Back
        p7 = [x_w_max, y_w_max, z_w_max] # Top-Right-Back
        
        cuboid_points = []
        for pt in [p0, p1, p2, p3, p4, p5, p6, p7]:
            cuboid_points.append([float(pt[0]), float(pt[1]), float(pt[2]), 1.0])
            
        return cuboid_points

    def project_sam_mask_to_3d_points(self, mask_bool):
        """
        Projects dense 3D points from a 2D SAM binary segmentation mask,
        extracts its boundary/contour, approximates it to a simplified 3D polygon,
        and returns the list of 3D world coordinates for the contour points.
        """
        import cv2
        obs = self.sim.get_sensor_observations()
        depth_img = obs.get("depth_sensor")
        if depth_img is None:
            return []
            
        h, w = depth_img.shape
        
        # Ensure mask shape matches depth image
        if mask_bool.shape != (h, w):
            mask_bool = cv2.resize(mask_bool.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
            
        # 1. Extract 2D boundary/contour using OpenCV
        mask_uint8 = (mask_bool.astype(np.uint8)) * 255
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return []
            
        # Get the largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        
        # 2. Approximate and simplify the contour to keep the point count small but extremely accurate
        epsilon = 0.015 * cv2.arcLength(largest_contour, True)
        approx_contour = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        # 3. Project only these simplified contour points to 3D using depth map
        contour_pts = approx_contour.reshape(-1, 2)
        
        hfov_rad = np.deg2rad(self.hfov)
        fx = (w / 2.0) / np.tan(hfov_rad / 2.0)
        fy = fx
        cx, cy = w / 2.0, h / 2.0
        
        sensor_node = self.agent.scene_node.node_sensor_suite.get("color_sensor").node
        T_wc = np.array(sensor_node.absolute_transformation())
        
        world_contour_points = []
        for pt in contour_pts:
            u, v = int(pt[0]), int(pt[1])
            u = min(w - 1, max(0, u))
            v = min(h - 1, max(0, v))
            
            d = float(depth_img[v, u])
            
            # If depth at exact contour is invalid/noisy, search locally in a 5x5 window
            if not (0.15 < d < 15.0):
                valid_depths = []
                for du in range(-2, 3):
                    for dv in range(-2, 3):
                        nu, nv = u + du, v + dv
                        if 0 <= nu < w and 0 <= nv < h:
                            nd = float(depth_img[nv, nu])
                            if 0.15 < nd < 15.0:
                                valid_depths.append(nd)
                if valid_depths:
                    d = float(np.median(valid_depths))
                else:
                    continue
                    
            x_c = (u - cx) * d / fx
            y_c = (cy - v) * d / fy
            z_c = -d
            P_c = np.array([x_c, y_c, z_c, 1.0])
            P_w = T_wc @ P_c
            world_contour_points.append([float(P_w[0]), float(P_w[1]), float(P_w[2]), 1.0])
            
        return world_contour_points

    def plan_path_with_sam_masks(self, obstacle_masks):
        """
        Projects obstacle SAM binary masks to 3D, plans a collision-free path to the door,
        and saves these for display and visual navigation.
        """
        def to_list3(v):
            """Safely convert any Habitat/PyGLM/numpy vector to a plain [x, y, z] list."""
            try:
                arr = np.array([float(v[0]), float(v[1]), float(v[2])])
                return arr.tolist()
            except Exception:
                return [float(v[0]), float(v[1]), float(v[2])]
        
        def is_nan_vec(v):
            """Safely check if a Habitat/PyGLM/numpy vector contains NaN."""
            try:
                return any(np.isnan(float(c)) for c in [v[0], v[1], v[2]])
            except Exception:
                return False

        self.detected_obstacles_3d = []
        self.planned_waypoints = []
        
        for mask in obstacle_masks:
            points_3d = self.project_sam_mask_to_3d_points(mask)
            if points_3d:
                self.detected_obstacles_3d.append(points_3d)
                
        agent_state = self.agent.get_state()
        agent_pos = agent_state.position
        
        # Determine door target center
        if hasattr(self, 'tracked_3d_points') and self.tracked_3d_points:
            door_points = np.array(self.tracked_3d_points)
            door_center = np.mean(door_points, axis=0)[:3]
        else:
            sensor_node = self.agent.scene_node.node_sensor_suite.get("color_sensor").node
            T_wc = np.array(sensor_node.absolute_transformation())
            forward_vec = T_wc[:3, 2] * -1
            door_center = np.array([float(agent_pos[0]), float(agent_pos[1]), float(agent_pos[2])]) + forward_vec * 3.0
            
        door_center_snapped = self.sim.pathfinder.snap_point(door_center)
        if is_nan_vec(door_center_snapped):
            door_center_snapped = door_center
            
        path = habitat_sim.ShortestPath()
        path.requested_start = agent_pos
        path.requested_end = door_center_snapped
        
        found_path = self.sim.pathfinder.find_path(path)
        
        obstacle_detected = False
        reason = "Clear path"
        turn_suggestion = "right"
        closest_obs_dist = 99.0
        
        if found_path and len(path.points) > 1:
            self.planned_waypoints = list(path.points)
            self.logical_waypoints = [to_list3(door_center_snapped)]
            
            if self.detected_obstacles_3d:
                # Flatten all projected obstacle points
                all_pts = []
                for obs_pts in self.detected_obstacles_3d:
                    for pt in obs_pts:
                        all_pts.append(np.array(pt[:3]))
                
                if all_pts:
                    all_pts = np.array(all_pts)
                    
                    # --- PATH INTERSECTION CHECK ---
                    # Only trigger a detour if an obstacle point is within PATH_CLEARANCE
                    # meters of any segment of the current planned path.
                    # If the obstacle is off to the side and doesn't block the route, skip it.
                    PATH_CLEARANCE = 0.45  # meters — minimum safe distance from path
                    
                    path_points_np = [np.array([float(p[0]), float(p[1]), float(p[2])]) for p in self.planned_waypoints]
                    
                    def point_to_segment_dist_xz(pt, seg_a, seg_b):
                        """Minimum XZ-plane distance from pt to segment [seg_a, seg_b]."""
                        p  = np.array([pt[0],    pt[2]])
                        a  = np.array([seg_a[0], seg_a[2]])
                        b  = np.array([seg_b[0], seg_b[2]])
                        ab = b - a
                        ab_len_sq = np.dot(ab, ab)
                        if ab_len_sq < 1e-8:
                            return np.linalg.norm(p - a)
                        t = np.clip(np.dot(p - a, ab) / ab_len_sq, 0.0, 1.0)
                        proj = a + t * ab
                        return np.linalg.norm(p - proj)
                    
                    path_blocked = False
                    min_obs_path_dist = 99.0
                    for obs_pt in all_pts:
                        for i in range(len(path_points_np) - 1):
                            d = point_to_segment_dist_xz(obs_pt, path_points_np[i], path_points_np[i+1])
                            if d < min_obs_path_dist:
                                min_obs_path_dist = d
                            if d < PATH_CLEARANCE:
                                path_blocked = True
                                break
                        if path_blocked:
                            break
                    
                    if not path_blocked:
                        # Obstacle exists visually but doesn't intersect the planned path.
                        # Keep current route unchanged — no detour needed.
                        reason = f"Obstacle detected but does not block path (min dist: {min_obs_path_dist:.2f}m). Keeping original route."
                        obstacle_detected = False
                    else:
                        # 1. Heading vector from agent to door snapped position (XZ plane)
                        door_dir_2d = np.array([door_center_snapped[0] - agent_pos[0], door_center_snapped[2] - agent_pos[2]])
                        door_dir_len = np.linalg.norm(door_dir_2d)
                        if door_dir_len > 1e-4:
                            u = door_dir_2d / door_dir_len
                        else:
                            u = np.array([1.0, 0.0])
                        
                        # Perpendicular vector pointing right (lateral direction)
                        p = np.array([-u[1], u[0]])
                        
                        # Project all obstacle points onto the perpendicular vector to find extreme left and right corners
                        obs_pts_2d = all_pts[:, [0, 2]]
                        lateral_offsets = np.dot(obs_pts_2d - np.array([agent_pos[0], agent_pos[2]]), p)
                        
                        left_idx = np.argmin(lateral_offsets)
                        right_idx = np.argmax(lateral_offsets)
                        
                        left_extreme = all_pts[left_idx]
                        right_extreme = all_pts[right_idx]
                        
                        # Generate left and right detour candidates with dynamic safety offset reduction if they fall off-mesh
                        left_snapped = None
                        left_valid = False
                        # Try decreasing safety offsets to find a valid navigable point in narrow passages
                        for offset in [0.50, 0.40, 0.30, 0.20, 0.15, 0.10]:
                            left_cand_2d = left_extreme[[0, 2]] - offset * p
                            left_cand_3d = np.array([left_cand_2d[0], agent_pos[1], left_cand_2d[1]])
                            snap = self.sim.pathfinder.snap_point(left_cand_3d)
                            if not is_nan_vec(snap):
                                # Also check if the snapped point is reasonably close to the candidate to prevent snapping to another room
                                dist_to_cand = np.linalg.norm(np.array(snap) - left_cand_3d)
                                if dist_to_cand < 1.0:
                                    left_snapped = snap
                                    left_valid = True
                                    break
                                
                        right_snapped = None
                        right_valid = False
                        for offset in [0.50, 0.40, 0.30, 0.20, 0.15, 0.10]:
                            right_cand_2d = right_extreme[[0, 2]] + offset * p
                            right_cand_3d = np.array([right_cand_2d[0], agent_pos[1], right_cand_2d[1]])
                            snap = self.sim.pathfinder.snap_point(right_cand_3d)
                            if not is_nan_vec(snap):
                                dist_to_cand = np.linalg.norm(np.array(snap) - right_cand_3d)
                                if dist_to_cand < 1.0:
                                    right_snapped = snap
                                    right_valid = True
                                    break
                        
                        # Choose the best sub-goal: prioritizes walkable/navigable path, then minimizes distance to door
                        if left_valid and not right_valid:
                            sub_goal_3d = np.array([float(left_snapped[0]), float(left_snapped[1]), float(left_snapped[2])])
                        elif right_valid and not left_valid:
                            sub_goal_3d = np.array([float(right_snapped[0]), float(right_snapped[1]), float(right_snapped[2])])
                        elif left_valid and right_valid:
                            # Both are valid, choose the one closer to the door center
                            dist_left = np.linalg.norm(np.array(left_snapped) - np.array(door_center_snapped))
                            dist_right = np.linalg.norm(np.array(right_snapped) - np.array(door_center_snapped))
                            if dist_left < dist_right:
                                sub_goal_3d = np.array([float(left_snapped[0]), float(left_snapped[1]), float(left_snapped[2])])
                            else:
                                sub_goal_3d = np.array([float(right_snapped[0]), float(right_snapped[1]), float(right_snapped[2])])
                        else:
                            # Fallback if both snap to NaN
                            fallback_left_cand_2d = left_extreme[[0, 2]] - 0.20 * p
                            fallback_left_cand_3d = np.array([fallback_left_cand_2d[0], agent_pos[1], fallback_left_cand_2d[1]])
                            sub_goal_3d = fallback_left_cand_3d
                            
                        # Generate two-segment path: Segment 1 (Agent -> Sub-goal), Segment 2 (Sub-goal -> Door)
                        path1 = habitat_sim.ShortestPath()
                        path1.requested_start = agent_pos
                        path1.requested_end = sub_goal_3d
                        found1 = self.sim.pathfinder.find_path(path1)
                        
                        path2 = habitat_sim.ShortestPath()
                        path2.requested_start = sub_goal_3d
                        path2.requested_end = door_center_snapped
                        found2 = self.sim.pathfinder.find_path(path2)
                        
                        combined_points = []
                        if found1 and len(path1.points) > 1:
                            combined_points.extend(path1.points)
                        else:
                            combined_points.append(to_list3(agent_pos))
                            combined_points.append(to_list3(sub_goal_3d))
                            
                        if found2 and len(path2.points) > 1:
                            combined_points.extend(path2.points[1:])
                        else:
                            combined_points.append(to_list3(door_center_snapped))
                            
                        self.planned_waypoints = combined_points
                        self.logical_waypoints = [to_list3(sub_goal_3d), to_list3(door_center_snapped)]
                        
                        # Calculate closest obstacle distance for status logging
                        closest_obs_dist = 99.0
                        for pt in all_pts:
                            dist = np.linalg.norm(agent_pos - pt)
                            if dist < closest_obs_dist:
                                closest_obs_dist = dist
                                
                        obstacle_detected = True
                        reason = f"Obstacle blocks path (path dist: {min_obs_path_dist:.2f}m). Detour active."
                        
                        # Determine turn suggestion relative to sub-goal
                        sensor_node = self.agent.scene_node.node_sensor_suite.get("color_sensor").node
                        T_wc = np.array(sensor_node.absolute_transformation())
                        T_cw = np.linalg.inv(T_wc)
                        sg_hom = np.array([sub_goal_3d[0], sub_goal_3d[1], sub_goal_3d[2], 1.0])
                        sg_c = T_cw @ sg_hom
                        if sg_c[0] > 0:
                            turn_suggestion = "right"
                        else:
                            turn_suggestion = "left"
                        
            obs = self.sim.get_sensor_observations()
            rgb = obs.get("color_sensor")
            if rgb is not None:
                rgb_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGBA2BGR)
                
                proj_wps = self.project_world_points_to_screen(self.planned_waypoints)
                h, w, _ = rgb_bgr.shape
                for i in range(len(proj_wps) - 1):
                    p1, p2 = proj_wps[i], proj_wps[i+1]
                    if not p1["behind"] and not p2["behind"]:
                        pt1 = (int(p1["x"] * w), int(p1["y"] * h))
                        pt2 = (int(p2["x"] * w), int(p2["y"] * h))
                        draw_dashed_line(rgb_bgr, pt1, pt2, (255, 0, 0), thickness=4)
                        
                for obs_points in self.detected_obstacles_3d:
                    proj_obs = self.project_world_points_to_screen(obs_points)
                    pts = []
                    for p in proj_obs:
                        if not p.get("behind"):
                            pts.append((int(p["x"] * w), int(p["y"] * h)))
                        else:
                            pts.append(None)
                    
                    if len(pts) >= 3:
                        valid_pts = [p for p in pts if p is not None]
                        if len(valid_pts) >= 3:
                            # Draw beautiful semi-transparent filled polygon
                            overlay = rgb_bgr.copy()
                            cv2.fillPoly(overlay, [np.array(valid_pts, dtype=np.int32)], (0, 0, 255))
                            cv2.addWeighted(overlay, 0.4, rgb_bgr, 0.6, 0, rgb_bgr)
                            # Draw border
                            cv2.polylines(rgb_bgr, [np.array(valid_pts, dtype=np.int32)], True, (0, 0, 255), 3)
                            
                status_text = f"OBSTACLE DETECTED: {closest_obs_dist:.2f}m" if obstacle_detected else "PATH CLEAR"
                cv2.putText(
                    rgb_bgr, 
                    status_text, 
                    (30, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    1.0, 
                    (0, 0, 255) if obstacle_detected else (0, 255, 0), 
                    3
                )
                
                # Save visual frame to output.jpg for dashboard
                cv2.imwrite("vlm_optimized_input_debug.jpg", rgb_bgr)
                cv2.imwrite("output.jpg", rgb_bgr)
                
        else:
            # Robust Fallback: If no path was found via pathfinder or it is too short,
            # plan a direct straight-line path to the target door center (since the floor is clear!)
            print("ShortestPath find_path failed or returned empty path. Falling back to direct straight-line interpolation.")
            steps = 5
            points = []
            for i in range(steps + 1):
                t = i / steps
                pt = np.array(agent_pos) * (1 - t) + np.array(door_center_snapped) * t
                points.append(pt.tolist())
            self.planned_waypoints = points
            self.logical_waypoints = [door_center_snapped.tolist()]
            reason = "Clear path (Direct Fallback)"
            
        return {
            "obstacle_detected": obstacle_detected,
            "distance": closest_obs_dist if obstacle_detected else 99.0,
            "turn_suggestion": turn_suggestion,
            "reason": reason
        }

    def plan_path_with_obstacles(self, obstacle_boxes):
        """Legacy compatibility wrapper. Converts bounding boxes to flat binary masks and delegates."""
        obs = self.sim.get_sensor_observations()
        depth_img = obs.get("depth_sensor")
        if depth_img is None:
            return {"obstacle_detected": False, "reason": "No sensor data"}
        h, w = depth_img.shape
        masks = []
        for box in obstacle_boxes:
            mask = np.zeros((h, w), dtype=bool)
            u_min = max(0, int(box[0] * w))
            v_min = max(0, int(box[1] * h))
            u_max = min(w - 1, int(box[2] * w))
            v_max = min(h - 1, int(box[3] * h))
            if u_min < u_max and v_min < v_max:
                mask[v_min:v_max, u_min:u_max] = True
            masks.append(mask)
        return self.plan_path_with_sam_masks(masks)

    def spawn_starter(self):
        """Spawns the agent at the deterministic starter point."""
        agent_state = self.agent.get_state()
        agent_state.position = self.starter_position
        agent_state.rotation = np.array([0, 0, 0, 1.0])
        self.agent.set_state(agent_state)
        self._apply_height_offset()
        return True, self.get_frame_as_base64()

    def reset_camera(self):
        """Resets the agent's rotation to default forward view."""
        state = self.agent.get_state()
        # Identity rotation (looking forward, level)
        state.rotation = np.array([0, 0, 0, 1.0]) # [x, y, z, w]
        self.agent.set_state(state)
        self._apply_height_offset()
        return self.get_frame_as_base64()

    def snap_to_floor(self):
        """Snaps the agent to the nearest navigable point on the floor."""
        state = self.agent.get_state()
        if self.sim.pathfinder.is_loaded:
            snapped = self.sim.pathfinder.snap_point(state.position)
            if not np.isnan(snapped).any():
                state.position = snapped
                self.agent.set_state(state)
        self._apply_height_offset()
        return self.get_frame_as_base64()

    def reset_agent(self):
        self.collision_count = 0
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

    def set_height_offset(self, offset):
        """Sets the vertical height offset and refreshes the view."""
        self.height_offset = offset
        self._apply_height_offset()
        return self.get_frame_as_base64()

    def get_memory_string(self):
        """Returns the current state records for prompt injection."""
        if len(self.memory) == 0:
            return "[Last Progress State: None]\n1. None\n2. None"
            
        def sanitize_action(action_str):
            # Brute-force: split by hyphen and take only the first part [Command] (State)
            if " - " in action_str:
                return action_str.split(" - ")[0].strip()
            return action_str.strip()

        last_item = self.memory[-1]
        state_match = re.search(r'\(State: (.*?)\)', last_item)
        last_state = state_match.group(1) if state_match else "None"
        header = f"[Last Progress State: {last_state}]"
        
        mem0 = sanitize_action(self.memory[0])
        if len(self.memory) == 1:
            return f"{header}\n1. None\n2. {mem0}"
        else:
            mem1 = sanitize_action(self.memory[1])
            return f"{header}\n1. {mem0}\n2. {mem1}"

    def record_vlm_action(self, command, reasoning, state="CORE"):
        """Updates the persistent memory with the latest AI decision."""
        self.memory.append(f"[{command}] (State: {state}) - {reasoning}")

    def clear_memory(self, reset_collisions=True, keep_drawings=False):
        """Clear historical memory."""
        self.memory.clear()
        if not keep_drawings:
            self.tracked_3d_points = []
            self.detected_obstacles_3d = []
            self.planned_waypoints = []
            self.logical_waypoints = []
        self.accumulated_obstacle_points = []
        if reset_collisions:
            self.collision_count = 0

    def analyze_floor_obstacles(self):
        """
        Analyzes the depth map to check for close obstacles on the floor level.
        Returns a dictionary with status and details.
        """
        obs = self.sim.get_sensor_observations()
        depth_img = obs.get("depth_sensor")
        if depth_img is None:
            return {"obstacle_detected": False, "reason": "No depth sensor"}

        h, w = depth_img.shape
        # Focus on the lower part of the screen and horizontally wider
        v_min = int(h * 0.6)
        v_max = int(h * 0.9)
        u_min = int(w * 0.2)
        u_max = int(w * 0.8)

        patch = depth_img[v_min:v_max, u_min:u_max]
        
        # Filter valid depth values
        valid_patch = patch[(patch > 0.0) & (patch < 10.0)]
        
        if valid_patch.size == 0:
            return {"obstacle_detected": False, "reason": "No valid depth readings"}
            
        # Use 5th percentile to ignore noise
        min_depth = float(np.percentile(valid_patch, 5))
        
        # Determine if obstacle is too close. Reduced threshold to 1.0m.
        threshold = 1.0
        if min_depth < threshold:
            # Check which side is clearer to suggest an avoidance turn
            left_patch = patch[:, :int(patch.shape[1]/2)]
            right_patch = patch[:, int(patch.shape[1]/2):]
            
            valid_left = left_patch[left_patch > 0.0]
            valid_right = right_patch[right_patch > 0.0]
            
            left_dist = float(np.median(valid_left)) if valid_left.size > 0 else 10.0
            right_dist = float(np.median(valid_right)) if valid_right.size > 0 else 10.0
            
            turn_suggestion = "right" if right_dist > left_dist else "left"
            
            # --- Obstacle detected: Mark and save screenshot ---
            rgb = obs.get("color_sensor")
            if rgb is not None:
                # Convert color frame to BGR for OpenCV
                rgb_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGBA2BGR)
                
                # Draw red marking rectangle
                cv2.rectangle(rgb_bgr, (u_min, v_min), (u_max, v_max), (0, 0, 255), 3)
                cv2.putText(
                    rgb_bgr, 
                    f"OBSTACLE DETECTED: {min_depth:.2f}m", 
                    (u_min + 15, v_min + 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.8, 
                    (0, 0, 255), 
                    2
                )
                # Save sequentially
                pass
            
            return {
                "obstacle_detected": True, 
                "distance": min_depth, 
                "turn_suggestion": turn_suggestion,
                "reason": f"Obstacle at {min_depth:.2f}m"
            }
        else:
            return {
                "obstacle_detected": False, 
                "distance": min_depth,
                "reason": f"Clear path (closest: {min_depth:.2f}m)"
            }

    def move_agent(self, action):
        """
        Action can be: 'move_forward', 'move_backward', 'turn_left', 'turn_right', 'look_up', 'look_down'
        and 30-degree variations: 'turn_left_30', 'turn_right_30', 'look_up_30', 'look_down_30'
        """
        if action == "look_down_40":
            import magnum as mn
            q = mn.Quaternion.rotation(mn.Deg(-40.0), mn.Vector3(1.0, 0.0, 0.0))
            for sensor_name in ["color_sensor", "depth_sensor"]:
                sensor_node = self.agent.scene_node.node_sensor_suite.get(sensor_name).node
                sensor_node.rotation = q
            self._apply_height_offset()
            return self.get_frame_as_base64()
        elif action == "look_up_40":
            import magnum as mn
            q = mn.Quaternion()
            for sensor_name in ["color_sensor", "depth_sensor"]:
                sensor_node = self.agent.scene_node.node_sensor_suite.get(sensor_name).node
                sensor_node.rotation = q
            self._apply_height_offset()
            return self.get_frame_as_base64()

        valid_actions = [
            "move_forward", "move_backward", 
            "turn_left", "turn_right", 
            "look_up", "look_down",
            "turn_left_5", "turn_right_5",
            "turn_left_10", "turn_right_10",
            "turn_left_15", "turn_right_15",
            "turn_left_20", "turn_right_20",
            "turn_left_30", "turn_right_30",
            "turn_left_40", "turn_right_40",
            "turn_left_90", "turn_right_90",
            "look_up_30", "look_down_30",
            "look_up_40", "look_down_40"
        ]
        
        if action in valid_actions:
            prev_pos = self.agent.get_state().position
            self.agent.act(action)
            curr_pos = self.agent.get_state().position
            
            collided = getattr(self.sim, 'previous_step_collided', False)
            if action in ["move_forward", "move_backward", "move_forward_small", "move_backward_small"] and action != "refresh":
                expected_amount = 0.05 if "small" in action else 0.25
                dist = np.linalg.norm(curr_pos - prev_pos)
                
                # High-precision contact check:
                # Slightly lowered sensitivity to prevent false triggers during light side-grazing:
                # - Standard steps (0.25m) use a 3.5cm (0.035m) tolerance (collision if dist < 0.215m)
                # - Small steps (0.05m) use a 1.2cm (0.012m) tolerance (collision if dist < 0.038m)
                tolerance = 0.012 if "small" in action else 0.035
                if dist < (expected_amount - tolerance):
                    collided = True
            
            if collided:
                self.collision_count += 1
            
            # Re-apply height offset after movement
            self._apply_height_offset()
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
            
            # Map colors based on Habitat values: 1 is navigable, 0 is invalid/obstacle, 2+ is border 
            color_map = np.zeros((topdown_map.shape[0], topdown_map.shape[1], 3), dtype=np.uint8)
            color_map[topdown_map == 1] = [255, 255, 255] # Walkable areas white
            color_map[topdown_map == 2] = [100, 100, 100] # Borders gray
            
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
            
            if np.any(np.isnan(snapped_pos)):
                # Fallback to current agent height if floor snap fails
                current_y = self.agent.get_state().position[1]
                target_pos[1] = current_y
                snapped_pos = self.sim.pathfinder.snap_point(target_pos)

            if np.any(np.isnan(snapped_pos)):
                return False, "Point is not navigable."
                
            agent_state = self.agent.get_state()
            agent_state.position = snapped_pos
            # Reset rotation to look forward when spawning
            agent_state.rotation = np.array([0, 0, 0, 1.0])
            self.agent.set_state(agent_state)
            self._apply_height_offset()
            
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
