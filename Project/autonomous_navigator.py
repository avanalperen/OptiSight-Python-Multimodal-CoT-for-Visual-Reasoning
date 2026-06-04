import time
import re
import json
import logging
import cv2
import numpy as np
import base64
import asyncio
from collections import deque

logger = logging.getLogger(__name__)

class AutonomousNavigator:
    def __init__(self, inference_callback, move_callback, execute_cmds=True):
        self._is_running = False
        self._is_paused = False
        
        # Wrapped callbacks that instantly abort if the navigation is stopped
        async def wrapped_move(action, bbox=None):
            if not self._is_running:
                raise asyncio.CancelledError("Navigation stopped")
            res = await move_callback(action, bbox)
            if not self._is_running:
                raise asyncio.CancelledError("Navigation stopped")
            return res

        async def wrapped_inference(prompt):
            if not self._is_running:
                raise asyncio.CancelledError("Navigation stopped")
            res = await inference_callback(prompt)
            if not self._is_running:
                raise asyncio.CancelledError("Navigation stopped")
            return res

        self.inference_callback = wrapped_inference
        self.move_callback = wrapped_move
        self.execute_cmds = execute_cmds
        
        self.goal = ""
        self.state = "SEARCHING" # [SEARCHING, FINDING, NAVIGATING, RECOVERING]
        self.memory = deque(maxlen=2)
        self.collision_flag = False
        self.last_command = None
        self.navigating_start_pose = None # To restore after collision
        self.pose_history = deque(maxlen=5) # To restore 5 steps back
        self.pass_sequence_triggered = False
        self.scenario = "scenario1"
        self.steps_since_last_scan = 0
        self.planned_waypoints = []
        self.detected_obstacles_3d = []
        self.camera_tilted_for_obstacle = False  # True = camera stays down during nav when obstacle found
        self.recovery_attempts = 0  # To track consecutive collisions
        
        # Tracking attributes for Visual Servoing
        self.visualize = True # Can be toggled
        self.locked_bbox = None # [x_min, y_min, x_max, y_max] normalized 0-1
        self.tracking_points = None # numpy array of points
        self.prev_gray = None
        self.servo_step_count = 0
        self.lk_params = dict(winSize=(21, 21), maxLevel=3,
                            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        
        # Default templates
        self.prompts = {
            "core": "", # Base template if needed, though we'll likely use 3 others
            "searching": """Task: Is there a door and door passage visible?
Note: Do not confuse wall corners, pillars, or shower cabin edges with doors. A door passage must be a clear opening meant for walking through into another room.
Respond ONLY with 'Yes' or 'No'. Do not explain.""",








            "navigating": """You are the OptiSight Visual Reasoning Core (NAVIGATING MODE).
GOAL: {goal}
STATE: NAVIGATING (Goal in Sight)
MEMORY: {memory}

[INSTRUCTIONS]
1. Goal is visible! Align with it using the GREEN Angle Grid lines.
2. The green lines are a VIRTUAL OVERLAY and NOT obstacles.
3. Advance toward the goal. Avoid obstacles.
4. strictly 1 sentence reasoning. output <cmd>COMMAND</cmd>.

Output Format:
Observation: (Max 15 words)
Goal_Check: (YES/NO)
Plan: (2 sub-steps)
Reasoning: (1 sentence)
<cmd>COMMAND</cmd>""",
            "finding": """You are the OptiSight Visual Reasoning Core (FINDING MODE).
GOAL: {goal}
STATE: FINDING (Confirming and Aligning with Goal)
MEMORY: {memory}

[INSTRUCTIONS]
1. Goal is spotted! Now, refine your position and align perfectly.
2. Use the GREEN Angle Grid to determine the exact direction.
3. strictly 1 sentence reasoning. output <cmd>COMMAND</cmd>.

Output Format:
Observation: (Max 15 words)
Goal_Check: (YES/NO)
Plan: (2 sub-steps)
Reasoning: (1 sentence)
<cmd>COMMAND</cmd>""",
            "stopping": """You are the OptiSight Visual Reasoning Core (STOPPING MODE).
GOAL: {goal}
STATE: STOPPING (Collision happened)
MEMORY: {memory}

[INSTRUCTIONS]
1. COLLISION DETECTED! You must stop and acknowledge the obstacle.
2. strictly 1 sentence reasoning. output <cmd>COMMAND</cmd>.
Valid: <cmd>Stop</cmd>.

Output Format:
Observation: (Max 15 words)
Goal_Check: (YES/NO)
Plan: (2 sub-steps)
Reasoning: (1 sentence)
<cmd>COMMAND</cmd>""",
            "recovering": """You are the OptiSight Visual Reasoning Core (RECOVERING MODE).
GOAL: {goal}
STATE: RECOVERING (Collision/Stuck)
MEMORY: {memory}

[INSTRUCTIONS]
1. You hit something! 
2. You MUST move backward or turn away to clear the path.
3. strictly 1 sentence reasoning. output <cmd>COMMAND</cmd>.

Output Format:
Observation: (Max 15 words)
Goal_Check: (YES/NO)
Plan: (2 sub-steps)
Reasoning: (1 sentence)
<cmd>COMMAND</cmd>"""
        }
        
        self.cmd_map = {
            "go ahead": "move_forward",
            "turn left": "turn_left_30",
            "turn right": "turn_right_30",
            "turn 10 degrees left": "turn_left",
            "turn 10 degrees right": "turn_right",
            "turn 20 degrees left": "turn_left_20",
            "turn 20 degrees right": "turn_right_20",
            "turn 30 degrees left": "turn_left_30",
            "turn 30 degrees right": "turn_right_30",
            "turn 40 degrees left": "turn_left_40",
            "turn 40 degrees right": "turn_right_40",
            "turn 90 degrees left": "turn_left_90",
            "turn 90 degrees right": "turn_right_90",
            "turn back": "move_backward",
            "task completed": "stop"
        }
        self._is_running = False
        self._streaming_active = False

    def update_settings(self, goal, prompts=None, initial_state="SEARCHING", scenario="scenario1"):
        self.goal = goal
        if initial_state:
            initial_state = initial_state.upper()
            if initial_state == "SCANNING":
                initial_state = "SCANNING_PATH"
        if not initial_state or initial_state not in ["SEARCHING", "FINDING", "SCANNING_PATH", "NAVIGATING", "RECOVERING"]:
            initial_state = "SEARCHING"
        self.state = initial_state
        self.scenario = scenario
        if prompts:
            self.prompts.update(prompts)
        self.memory.clear()
        self.pass_sequence_triggered = False
        self.collision_flag = False
        self.locked_bbox = None
        self.pose_history.clear()
        self.navigating_start_pose = None
        self.planned_waypoints = []
        self.detected_obstacles_3d = []
        self.recovery_attempts = 0
        
    def set_running(self, state: bool):
        self._is_running = state
        if not state:
            cv2.destroyAllWindows()
            self.state = "SEARCHING"
            self.memory.clear()
            self.collision_flag = False
            self.last_command = None
            self.navigating_start_pose = None
            self.pose_history.clear()
            self.pass_sequence_triggered = False
            self.steps_since_last_scan = 0
            self.planned_waypoints = []
            self.detected_obstacles_3d = []
            self.camera_tilted_for_obstacle = False
            self.recovery_attempts = 0
            self.locked_bbox = None
            self.tracking_points = None
            self.prev_gray = None
            self.servo_step_count = 0

    def start_visual_servo(self, bbox):
        """Transition to NAVIGATING with a provided bounding box to begin tracking."""
        self.locked_bbox = bbox
        self.state = "NAVIGATING"
        # Reset tracking points to force re-initialization on next frame
        self.tracking_points = None
        self.prev_gray = None
        self.pass_sequence_triggered = False
        logger.info(f"Visual Servo started with bbox: {bbox}")

    def get_auto_align_command(self, projection_info):
        """
        Decides the next centering step based on 3D coordinates.
        Uses a dynamic deadband: closer doors require tighter alignment.
        """
        if not projection_info or not projection_info.get("corners"):
            return "move_forward"
            
        corners = projection_info["corners"]
        valid_corners = [c for c in corners if not c.get("behind")]
        
        if not valid_corners:
            return "move_forward"
            
        xs = [c["x"] for c in valid_corners]
        center_x = sum(xs) / len(xs)
        door_width = max(xs) - min(xs)
        
        # --- DYNAMIC DEADBAND ---
        # Far (width < 0.3): deadband 0.10 (0.45 to 0.55)
        # Medium (width 0.3-0.6): deadband 0.08 (0.46 to 0.54)
        # Close (width > 0.6): deadband 0.12 (0.44 to 0.56) - Widened to prevent oscillation near door
        if door_width < 0.3:
            deadband = 0.10
        elif door_width < 0.6:
            deadband = 0.08
        else:
            deadband = 0.12
            
        lower_limit = 0.5 - (deadband / 2)
        upper_limit = 0.5 + (deadband / 2)
        
        # --- DYNAMIC PROPORTIONAL TURNING ---
        # Scale down turn intensity as we get closer (door_width increases)
        error = center_x - 0.5 # Positive = right, Negative = left
        
        turn_multiplier = 1.0
        if door_width > 0.6:
            turn_multiplier = 0.25 # Close: 1/4 intensity
        elif door_width > 0.3:
            turn_multiplier = 0.5  # Medium: 1/2 intensity
            
        if abs(error) > 0.15:
            # Base angles for different error ranges
            if abs(error) > 0.35:
                base_deg = 40
            elif abs(error) > 0.25:
                base_deg = 30
            else:
                base_deg = 20
                
            deg = int(base_deg * turn_multiplier)
            
            # Constrain to supported Habitat actions: [5, 10, 15, 20, 30, 40]
            allowed = [5, 10, 15, 20, 30, 40]
            deg = min(allowed, key=lambda x: abs(x - deg))
            
            return f"turn_right_{deg}" if error > 0 else f"turn_left_{deg}"
        elif center_x < lower_limit:
            return "turn_left_5"
        elif center_x > upper_limit:
            return "turn_right_5"
        else:
            return "move_forward"

    def get_auto_align_command_for_center_x(self, center_x):
        """Calculates rotation/forward commands to center the camera on a waypoint."""
        lower_limit = 0.44
        upper_limit = 0.56
        error = center_x - 0.5
        
        if abs(error) > 0.15:
            if abs(error) > 0.35:
                deg = 30
            elif abs(error) > 0.25:
                deg = 20
            else:
                deg = 10
            return f"turn_right_{deg}" if error > 0 else f"turn_left_{deg}"
        elif center_x < lower_limit:
            return "turn_left_5"
        elif center_x > upper_limit:
            return "turn_right_5"
        else:
            return "move_forward"

    def get_reverse_command(self, cmd):
        """Returns the inverse of a movement command to back away from a collision."""
        if not cmd: return "move_backward"
        if cmd == "move_forward": return "move_backward"
        if cmd == "move_backward": return "move_forward"
        if cmd == "turn_left": return "turn_right"
        if cmd == "turn_right": return "turn_left"
        if "turn_left_" in cmd: return cmd.replace("left", "right")
        if "turn_right_" in cmd: return cmd.replace("right", "left")
        return "move_backward" # Fallback

    def process_manual_step(self, frame_b64, projection_info=None):
        """
        Updates tracking and state transitions for manual mode.
        Returns (frame_b64, tracking_info)
        """
        if self.state not in ["OPTICAL_SERVOING", "NAVIGATING"]:
            return frame_b64, None

        tracking_info = None

        if self.state in ["OPTICAL_SERVOING", "NAVIGATING"]:
            if projection_info and projection_info.get("corners"):
                # Use 3D projection to update tracking bounds and check for pass completion
                corners = projection_info["corners"]
                xs = [c["x"] for c in corners]
                x_min = min(xs)
                x_max = max(xs)
                
                tracking_info = {"x_min": x_min, "x_max": x_max}
                
                # Check if passed: Boundaries exited frame [0, 1]
                if x_min <= 0.0 and x_max >= 1.0:
                    if not getattr(self, "pass_sequence_triggered", False):
                        self.pass_sequence_triggered = True
                        logger.info("Manual 3D pass detected! Signaling for automatic clearing.")
                        tracking_info = "PASS_DETECTED"
                        return frame_b64, tracking_info
            else:
                # If no projection yet, just keep current state
                pass

        return frame_b64, tracking_info

    def trigger_collision(self):
        """External call to flag a collision for the next iteration."""
        self.collision_flag = True

    def format_sse(self, event_type, data):
        """Format data as Server-Sent Events"""
        if isinstance(data, str):
            data = data.replace('\n', ' ')
        
        # If data is a dictionary (like move_res), extract frame and projection_info
        # to ensure the frontend receives what it expects.
        payload_data = data
        if isinstance(data, dict) and event_type == 'frame_update':
            # This allows sending both frame and projection_info in one go
            pass # Keep as dict
            
        payload = json.dumps({'type': event_type, 'data': payload_data})
        return f"data: {payload}\n\n"

    async def navigate_stream(self):
        """Generator function for Flask/FastAPI SSE streaming."""
        self._streaming_active = True
        self._is_running = True
        self._is_paused = False
        
        try:
            logger.info(f"Autonomous Navigation started in state: {self.state}")
        
            while self._is_running:
                if self._is_paused:
                    await asyncio.sleep(0.5)
                    continue
                    
                # Sanitize state to be absolutely robust
                if self.state:
                    self.state = self.state.upper()
                    if self.state == "SCANNING":
                        self.state = "SCANNING_PATH"
                if not self.state or self.state not in ["SEARCHING", "FINDING", "SCANNING_PATH", "NAVIGATING", "RECOVERING"]:
                    self.state = "SEARCHING"
                
                # Check for external collision trigger or if started/placed in RECOVERING state
                if self.collision_flag or self.state == "RECOVERING":
                    logger.warning("Collision detected or started in RECOVERING state. Switching to RECOVERING state.")
                    self.state = "RECOVERING"
                    self.collision_flag = False
                    self.recovery_attempts += 1
                    
                    yield self.format_sse('state_update', {"state": "RECOVERING"})
                    yield self.format_sse('log', f"[System] Collision detected (Attempt {self.recovery_attempts})! Waiting 2s before recovery sequence...")
                    
                    await asyncio.sleep(2.0)
                    
                    # Quick exit if stopped
                    if not self._is_running:
                        break
                    
                    reverse_cmd = self.get_reverse_command(self.last_command)
                    logger.info(f"Recovery: Executing smooth {reverse_cmd} sequence.")
                    
                    # Determine steps and sub-commands for smoothing
                    if "turn" in reverse_cmd:
                        steps = 9 if "90" in self.last_command or "90" in str(reverse_cmd) else 3 # 90 deg -> 9 steps, others -> 3
                        # Map turn_left_5 back to turn_right etc.
                        sub_cmd = "turn_left" if "left" in reverse_cmd else "turn_right"
                    else:
                        steps = 5
                        sub_cmd = "move_backward" if "backward" in reverse_cmd else "move_forward"
                    
                    yield self.format_sse('log', f"Recovery: Moving back smoothly ({steps} steps of {sub_cmd})...")
                    
                    recovery_collision = False
                    for i in range(steps):
                        if not self._is_running:
                            break
                        
                        move_res = await self.move_callback(sub_cmd)
                        if move_res:
                            yield self.format_sse('frame_update', move_res)
                            
                        # If we collide during recovery, stop immediately and return to SEARCHING
                        if self.collision_flag:
                            recovery_collision = True
                            break
                            
                        await asyncio.sleep(0.1)
                        
                    if recovery_collision:
                        yield self.format_sse('log', "[Recovery] Second collision detected during recovery! Aborting recovery. Stopping here and returning to SEARCHING.")
                        self.collision_flag = False
                        
                        # Restore camera to upright if it was tilted down
                        if self.camera_tilted_for_obstacle:
                            yield self.format_sse('log', "[Camera] Restoring camera to upright position...")
                            move_res = await self.move_callback("look_up_40")
                            if move_res:
                                yield self.format_sse('frame_update', move_res)
                            await asyncio.sleep(1.0)
                            self.camera_tilted_for_obstacle = False
                            
                        self.state = "SEARCHING"
                        self.recovery_attempts = 0
                        await asyncio.sleep(1.0)
                        continue
                        
                    if not self._is_running:
                        break
                    
                    await asyncio.sleep(1.0) # Pause after recovery move
                    
                    if self.recovery_attempts == 1 and self.planned_waypoints:
                        self.state = "NAVIGATING"
                        yield self.format_sse('log', "Recovery complete (Attempt 1). Retrying active path...")
                    else:
                        # Attempt 2+ or no planned waypoints
                        # Reset all stale navigation state to force a fresh threshold re-detection in SEARCHING
                        self.planned_waypoints = []
                        self.detected_obstacles_3d = []
                        self.locked_bbox = None
                        self.recovery_attempts = 0
                        
                        # Clear 3D projections on simulator to get a clean slate
                        move_res = await self.move_callback("clear_3d")
                        if move_res:
                            yield self.format_sse('frame_update', move_res)
                            
                        # Restore camera to upright if it was tilted down
                        if self.camera_tilted_for_obstacle:
                            yield self.format_sse('log', "[Camera] Restoring camera to upright position...")
                            move_res = await self.move_callback("look_up_40")
                            if move_res:
                                yield self.format_sse('frame_update', move_res)
                            await asyncio.sleep(1.0)
                            self.camera_tilted_for_obstacle = False
                            
                        self.state = "SEARCHING"
                        yield self.format_sse('log', "Recovery complete (Attempt 2). Route cleared. Returning to SEARCHING to re-detect threshold.")
                    continue

                # Build memory string
                mem_lines = []
                if len(self.memory) == 0:
                    mem_lines = ["1. None", "2. None"]
                elif len(self.memory) == 1:
                    mem_lines = ["1. None", f"2. {self.memory[0]}"]
                else:
                    mem_lines = [f"1. {self.memory[0]}", f"2. {self.memory[1]}"]
                mem_str = "\n".join(mem_lines)
                
                # Select appropriate template
                template_key = self.state.lower()
                state_template = self.prompts.get(template_key, self.prompts.get("searching"))
                core_template = self.prompts.get("core", "")
                
                # Merge Core + State templates (EXCEPT for SEARCHING state which should be minimal)
                if self.state == "SEARCHING":
                    full_template = state_template
                else:
                    full_template = core_template + "\n\n" + state_template if core_template else state_template
                
                prompt = full_template.replace("{goal}", self.goal).replace("{memory}", mem_str).replace("{state}", self.state).replace("{current_state}", self.state)
                
                yield self.format_sse('state_update', {"state": self.state})
                # We log "Analyzing" later if we actually hit the VLM inference part


                # --- PURE VISUAL SERVOING STATES ---
                
                if self.state == "NAVIGATING":
                    yield self.format_sse('log', "Navigating towards target..."
                        + (" [Camera tilted — obstacle evasion]" if self.camera_tilted_for_obstacle else ""))
                    
                    pass_complete = False
                    lost_proj_count = 0
                    while not pass_complete and self.state == "NAVIGATING" and self._is_running:
                        # 1. Get current position and projection
                        move_res = await self.move_callback("refresh")
                        if not move_res: break
                        if self.collision_flag:
                            self.state = "RECOVERING"
                            break
                        
                        # Yield current frame with projection overlay
                        yield self.format_sse('frame_update', move_res)
                        
                        agent_pos = move_res.get("agent_pos")
                        waypoints_3d = move_res.get("waypoints_3d", [])
                        proj_info = move_res.get("projection_info")
                        
                        # Update our local waypoints list (only if backend explicitly returned new ones)
                        if waypoints_3d:
                            self.planned_waypoints = waypoints_3d
                            
                        # If waypoints are present, follow them!
                        if self.planned_waypoints:
                            w_next = self.planned_waypoints[0]
                            # Guard against None agent_pos which would crash np.linalg.norm
                            if agent_pos is None:
                                yield self.format_sse('log', "[Warning] Agent position not available yet. Moving forward...")
                                move_res = await self.move_callback("move_forward")
                                if move_res: yield self.format_sse('frame_update', move_res)
                                await asyncio.sleep(0.2)
                                continue
                            dist = np.linalg.norm(np.array(agent_pos) - np.array(w_next))
                            
                            # If close to waypoint, pop it!
                            if dist < 0.30:
                                yield self.format_sse('log', f"Waypoint reached (dist: {dist:.2f}m). Proceeding to next.")
                                move_res = await self.move_callback("pop_waypoint")
                                if move_res:
                                    yield self.format_sse('frame_update', move_res)
                                    self.planned_waypoints = move_res.get("waypoints_3d", [])
                                    proj_info = move_res.get("projection_info")
                                    
                                if not self.planned_waypoints:
                                    # Reached final waypoint, execute final doorway passage
                                    yield self.format_sse('log', "Final waypoint reached. Executing final door passage...")
                                    for i in range(3):
                                        if self.collision_flag: break
                                        yield self.format_sse('log', f"Passing through doorway step {i+1}/3")
                                        move_res = await self.move_callback("move_forward")
                                        if move_res: yield self.format_sse('frame_update', move_res)
                                        await asyncio.sleep(0.3)
                                        
                                    if self.collision_flag:
                                        self.state = "RECOVERING"
                                        break
                                        
                                    # Restore camera to upright if it was tilted for obstacle evasion
                                    if self.camera_tilted_for_obstacle:
                                        # Camera was at -40°, restore fully upright with look_up_40
                                        move_res = await self.move_callback("look_up_40")
                                        if move_res: yield self.format_sse('frame_update', move_res)
                                        await asyncio.sleep(0.5)
                                        self.camera_tilted_for_obstacle = False
                                        
                                    # Clear all dynamic 3D projections, paths, and obstacles from memory upon success
                                    move_res = await self.move_callback("clear_3d")
                                    if move_res:
                                        self.planned_waypoints = []
                                        yield self.format_sse('frame_update', move_res)
                                        
                                    yield self.format_sse('log', "SUCCESS: Door passage completed. Robot stabilized.")
                                    yield self.format_sse('stopped', True)
                                    yield self.format_sse('success', "DOOR_PASSED")
                                    self.recovery_attempts = 0
                                    self._is_running = False
                                    break
                                continue
                                
                            # Align and move towards next waypoint
                            if proj_info and proj_info.get("route") and len(proj_info["route"]) > 0:
                                wp_proj = proj_info["route"][0]
                                if not wp_proj.get("behind"):
                                    center_x = wp_proj["x"]
                                    align_cmd = self.get_auto_align_command_for_center_x(center_x)
                                    
                                    self.last_command = align_cmd
                                    yield self.format_sse('log', f"Following path: {align_cmd} (Waypoint X: {center_x:.2f}, Dist: {dist:.2f}m)")
                                    
                                    move_res = await self.move_callback(align_cmd)
                                    if move_res: yield self.format_sse('frame_update', move_res)
                                    if self.collision_flag:
                                        self.state = "RECOVERING"
                                        break
                                        
                                    # Trigger Stop-and-Go scanning every 15 steps
                                    if self.scenario != "scenario1":
                                        self.steps_since_last_scan += 1
                                        if self.steps_since_last_scan >= 15:
                                            yield self.format_sse('log', "Periodic autopilot scan triggered.")
                                            self.state = "SCANNING_PATH"
                                            break
                                else:
                                    # Projected point is behind, skip it
                                    yield self.format_sse('log', "[Warning] Waypoint is behind camera. Skipping.")
                                    move_res = await self.move_callback("pop_waypoint")
                                    if move_res:
                                        self.planned_waypoints = move_res.get("waypoints_3d", [])
                            else:
                                # Fallback forward step
                                yield self.format_sse('log', "[Warning] Lost route visual projection. Reverting to forward step.")
                                move_res = await self.move_callback("move_forward")
                                if move_res: yield self.format_sse('frame_update', move_res)
                                if self.collision_flag:
                                    self.state = "RECOVERING"
                                    break
                                    
                        else:
                            # Fallback: No planned waypoints, align using traditional door threshold servoing!
                            if not proj_info or not proj_info.get("corners"):
                                lost_proj_count += 1
                                if lost_proj_count > 3:
                                    yield self.format_sse('log', "[Error] Repeatedly lost 3D Projection. Stopping navigation.")
                                    self._is_running = False
                                    break
                                yield self.format_sse('log', "[Warning] Lost 3D Projection info. Reverting to basic forward.")
                                move_res = await self.move_callback("move_forward")
                                if move_res: yield self.format_sse('frame_update', move_res)
                                if self.collision_flag:
                                    self.state = "RECOVERING"
                                    break
                                continue
                                
                            lost_proj_count = 0
                            corners = proj_info["corners"]
                            xs = [c["x"] for c in corners]
                            x_min, x_max = min(xs), max(xs)
                            center_x = sum(xs) / len(xs)
                            door_width = x_max - x_min
                            
                            if (x_min <= 0.0 and x_max >= 1.0) or door_width > 1.2:
                                yield self.format_sse('log', f"Door threshold reached (Width: {door_width:.2f}). Executing final passage...")
                                for i in range(3):
                                    if self.collision_flag: break
                                    yield self.format_sse('log', f"Passing through doorway step {i+1}/3")
                                    move_res = await self.move_callback("move_forward")
                                    if move_res: yield self.format_sse('frame_update', move_res)
                                    await asyncio.sleep(0.3)
                                    
                                if self.collision_flag:
                                    self.state = "RECOVERING"
                                    break
                                    
                                yield self.format_sse('log', "SUCCESS: Door passage completed. Robot stabilized.")
                                yield self.format_sse('stopped', True)
                                yield self.format_sse('success', "DOOR_PASSED")
                                self.recovery_attempts = 0
                                self._is_running = False
                                break
                                
                            align_cmd = self.get_auto_align_command(proj_info)
                            if "turn" in align_cmd:
                                reason = f"Hizalanma (Sadece Dönüş): {align_cmd} (Hedef X: {center_x:.2f})"
                                self.last_command = align_cmd
                                yield self.format_sse('log', reason)
                                move_res = await self.move_callback(align_cmd)
                                if move_res: yield self.format_sse('frame_update', move_res)
                                if self.collision_flag:
                                    self.state = "RECOVERING"
                                    break
                                    
                                await asyncio.sleep(0.1)
                                
                                self.state = "SCANNING_PATH"
                                break
                                
                            is_close = door_width > 0.6
                            action = "move_forward"
                            reason = f"Hizalı: Kapıya doğru ilerleme (0.25m)"
                            
                            self.last_command = action
                            yield self.format_sse('log', reason)
                            move_res = await self.move_callback(action)
                            if move_res: yield self.format_sse('frame_update', move_res)
                            if self.collision_flag:
                                self.state = "RECOVERING"
                                break
                                
                            await asyncio.sleep(0.1)
                            
                            self.steps_since_last_scan += 1
                            if self.steps_since_last_scan >= 15:
                                yield self.format_sse('log', "Periodic autopilot scan triggered.")
                                self.state = "SCANNING_PATH"
                                break
                                    
                        await asyncio.sleep(0.1)
                    
                    continue

                # --- FINDING STATE: Grounded-SAM lock onto door ---
                if self.state == "FINDING":
                    yield self.format_sse('log', "FINDING mode active: Waiting for Grounded-SAM lock...")
                    
                    sam_box_match = None
                    attempts = 0
                    while not sam_box_match and self._is_running:
                        if self.collision_flag:
                            self.state = "RECOVERING"
                            break
                        attempts += 1
                        yield self.format_sse('log', f"Grounded-SAM: Running inference (Attempt {attempts})...")
                        sam_response = await self.inference_callback("[SAM_ONLY]")
                        
                        # Stream the observation to the UI so the user sees SAM progress
                        yield self.format_sse('reasoning_chunk', sam_response + "<br>")
                        
                        # Robust parse for SAM box
                        sam_box_content_match = re.search(r'<box>(.*?)</box>', sam_response, re.DOTALL | re.IGNORECASE)
                        if sam_box_content_match:
                            coords_str = re.findall(r'\d+(?:\.\d+)?', sam_box_content_match.group(1))
                            if len(coords_str) == 4:
                                coords = [float(c) for c in coords_str]
                                scale = 1000.0 if max(coords) > 1.1 else 1.0
                                sam_box_match = {
                                    "x_min": coords[0] / scale,
                                    "y_min": coords[1] / scale,
                                    "x_max": coords[2] / scale,
                                    "y_max": coords[3] / scale
                                }
                        
                        if not sam_box_match:
                            if attempts >= 3:
                                yield self.format_sse('log', "[Warning] Grounded-SAM repeatedly failed to lock onto a door. Reverting to SEARCHING mode.")
                                self.state = "SEARCHING"
                                break
                            await asyncio.sleep(0.5) 
                    
                    if not self._is_running: break
                    if self.state == "SEARCHING": continue # Re-start loop in SEARCHING state
                    
                    if self.state == "RECOVERING" or self.collision_flag:
                        self.state = "RECOVERING"
                        continue
                    
                    # 2. Threshold Success: Draw and Wait 2s
                    try:
                        self.locked_bbox = [sam_box_match["x_min"], sam_box_match["y_min"], sam_box_match["x_max"], sam_box_match["y_max"]]
                        
                        # Call clear_3d to instantly purge any stale 3D projection points
                        move_res = await self.move_callback("clear_3d")
                        if move_res:
                            yield self.format_sse('frame_update', move_res)
                        
                        # Yield the highly precise 2D Grounded-SAM box
                        yield self.format_sse('sam_update', {"box": sam_box_match})
                        yield self.format_sse('log', "Threshold identified and drawn. Waiting 2s for visualization...")
                        await asyncio.sleep(2.0)
                        
                        # Clear threshold box BEFORE activating 3D Projection
                        yield self.format_sse('log', "Clearing threshold box...")
                        yield self.format_sse('sam_update', {"box": None})
                        await asyncio.sleep(0.5)
                        
                        # 3. 3D Projection: Apply and Wait 2s
                        if self.locked_bbox:
                            yield self.format_sse('log', "Auto-activating 3D Projection...")
                            move_res = await self.move_callback("start_3d", bbox=self.locked_bbox)
                            self.locked_bbox = None 
                            if move_res:
                                yield self.format_sse('frame_update', move_res)
                                
                        yield self.format_sse('log', "3D Projection active. Waiting 2s for visualization...")
                        await asyncio.sleep(2.0)
                        
                        # 4. Transition to SCANNING_PATH (or directly to NAVIGATING in Scenario 1)
                        if self.scenario == "scenario1":
                            yield self.format_sse('log', "Scenario 1: Bypassing obstacle avoidance, planning direct path to door...")
                            move_res = await self.move_callback("plan_direct_path")
                            if move_res:
                                self.planned_waypoints = move_res.get("waypoints_3d", [])
                                yield self.format_sse('frame_update', move_res)
                            yield self.format_sse('log', f"Scenario 1: Direct path planned with {len(self.planned_waypoints)} waypoints. Transitioning to NAVIGATING.")
                            self.state = "NAVIGATING"
                        else:
                            self.state = "SCANNING_PATH"
                            yield self.format_sse('log', "Transitioning to SCANNING_PATH for obstacle detection.")
                        continue # Restart loop in new state
                        
                    except Exception as e:
                        logger.error(f"FINDING sequence error: {e}")
                        self.state = "SEARCHING" # Fallback on error
                        continue

                # --- SCANNING_PATH STATE: Floor obstacle scan ---
                if self.state == "SCANNING_PATH":
                    yield self.format_sse('log', "Scanning floor for obstacles (Tilted view)...")
                    
                    # 1. Look Down to scan the floor (only if camera is not already tilted)
                    if not self.camera_tilted_for_obstacle:
                        move_res = await self.move_callback("look_down_40")
                        if move_res: yield self.format_sse('frame_update', move_res)
                        await asyncio.sleep(1.0) # Wait for tilt to stabilize and user to see
                    else:
                        yield self.format_sse('log', "[Camera] Head is already tilted down (-40°). Keeping camera at current fixed tilt.")
                    
                    route_status = "safe"
                    
                    # 2. Run Grounding SAM and Pathfinder using SAM Segmentation masks
                    yield self.format_sse('log', "Executing Grounded-SAM obstacle detection & SAM-mask 3D projection...")
                    analysis_res = await self.move_callback("analyze_floor")
                    if analysis_res:
                        obs_info = analysis_res.get("obstacle_info", {})
                        
                        # --- STEP A: Render obstacles first and pause 2 seconds ---
                        self.detected_obstacles_3d = analysis_res.get("obstacles_3d", [])
                        self.planned_waypoints = [] # Keep waypoints empty first so they don't draw yet!
                        
                        # Push update so only obstacles are drawn (in Orange)
                        partial_res = analysis_res.copy()
                        partial_res["waypoints_3d"] = []
                        yield self.format_sse('frame_update', partial_res)
                        
                        if obs_info.get("obstacle_detected"):
                            yield self.format_sse('log', f"<span style='color:#fca311'><b>[Obstacle Detected]</b> {obs_info.get('reason')} - Pausing 2s to visualize SAM-based obstacle projection...</span>")
                            await asyncio.sleep(2.0)
                            
                            # --- STEP B: Render planned waypoints and pause another 2 seconds ---
                            self.planned_waypoints = analysis_res.get("waypoints_3d", [])
                            yield self.format_sse('frame_update', analysis_res)
                            yield self.format_sse('log', "<span style='color:#00bfff'><b>[Safe Route Formulated]</b> 3D navigation path plotted around obstacle. Pausing 2s to visualize route...</span>")
                            await asyncio.sleep(2.0)
                            route_status = "evade"
                        else:
                            yield self.format_sse('log', f"<span style='color:#4ec9b0'><b>[Floor Clear]</b> {obs_info.get('reason')} - Pausing 2s for confirmation...</span>")
                            await asyncio.sleep(2.0)
                            
                            # Draw straight path to door since it is clear
                            self.planned_waypoints = analysis_res.get("waypoints_3d", [])
                            yield self.format_sse('frame_update', analysis_res)
                            yield self.format_sse('log', "<span style='color:#00bfff'><b>[Direct Route Formulated]</b> Direct 3D navigation path plotted. Pausing 2s to visualize route...</span>")
                            await asyncio.sleep(2.0)
                            route_status = "safe"
                            
                        self.steps_since_last_scan = 0
                    
                    # 3. Conditionally restore camera based on obstacle status
                    if route_status == "evade":
                        # Obstacle found: keep camera fully at -40° (same as scan angle)
                        # so the robot can see the floor path while navigating around the obstacle
                        self.camera_tilted_for_obstacle = True
                        yield self.format_sse('log', "<span style='color:#fca311'>[Camera] Keeping camera at scan angle (-40°) — obstacle evasion mode active.</span>")
                    else:
                        # No obstacle: restore camera fully upright
                        self.camera_tilted_for_obstacle = False
                        move_res = await self.move_callback("look_up_40")
                        if move_res: yield self.format_sse('frame_update', move_res)
                        await asyncio.sleep(1.0) # Wait for tilt to stabilize
                    
                    # 4. Transition to Navigating
                    self.state = "NAVIGATING"
                    
                    # Emit route waypoint overlay event
                    yield self.format_sse('route_update', {"status": route_status})
                    
                    yield self.format_sse('log', "Safe path verified. Resuming navigation.")
                    continue

                # --- STOPPING STATE ---
                if self.state == "STOPPING":
                    self.state = "RECOVERING"
                    yield self.format_sse('log', "Transitioning to RECOVERING.")
                    continue

                # --- STANDARD VLM NAVIGATION (SEARCHING only) ---
                # FINDING, SCANNING_PATH, NAVIGATING are handled above with 'continue'
                # so we only reach here in SEARCHING state.
                if self.state != "SEARCHING":
                    # Safety guard: if somehow we reach here in a non-SEARCHING state,
                    # just restart the loop cleanly without touching VLM.
                    await asyncio.sleep(0.1)
                    continue

                if self.state == "SEARCHING":
                    try:
                        response = await self.inference_callback(prompt)
                    except Exception as e:
                        yield self.format_sse('error', f"Inference failed: {str(e)}")
                        self._is_running = False
                        break
                        
                    if not self._is_running:
                        break
                             # 2. Parse Response (Robust for both simple Yes/No and structured formats)
                    box_content_match = re.search(r'<box>(.*?)</box>', response, re.DOTALL | re.IGNORECASE)
                    cmd_match = re.search(r'<cmd>(.*?)</cmd>', response, re.IGNORECASE)
                    
                    obs_match = re.search(r'Observation:\s*(.*?)(?=\n*(?:Goal_Check|Plan|Reasoning|<cmd>|<box>)|$)', response, re.IGNORECASE | re.DOTALL)
                    goal_match = re.search(r'Goal_Check:\s*(.*?)(?=\n*(?:Plan|Reasoning|<cmd>|<box>)|$)', response, re.IGNORECASE)
                    
                    observation = obs_match.group(1).strip() if obs_match else response.strip()
                    goal_check = goal_match.group(1).strip() if goal_match else "UNKNOWN"
                    
                    # Handle Bounding Box if present (from VLM)
                    parsed_box = None
                    if box_content_match:
                        try:
                            # Extract all numbers (integers or floats)
                            coords_str = re.findall(r'\d+(?:\.\d+)?', box_content_match.group(1))
                            if len(coords_str) == 4:
                                coords = [float(c) for c in coords_str]
                                scale = 1000.0 if max(coords) > 1.1 else 1.0
                                parsed_box = {
                                    "x_min": coords[0] / scale,
                                    "y_min": coords[1] / scale,
                                    "x_max": coords[2] / scale,
                                    "y_max": coords[3] / scale
                                }
                                # Coarse VLM box is used purely for state transition logic.
                                # We do NOT draw it or store it to prevent any incorrect/absurd threshold boxes from rendering.
                                logger.info(f"VLM coarse box detected: {parsed_box}. Switch to FINDING for precise Grounded-SAM lock.")
                        except Exception as e:
                            logger.error(f"Failed to parse box from response: {e}")
                    
                    # Fallback for bare Yes/No/Clear responses in ANY state
                    if goal_check == "UNKNOWN":
                        clean_resp = response.strip().upper()
                        if "YES" in clean_resp or "GOAL SPOTTED" in clean_resp or (parsed_box is not None and self.state == "FINDING"): 
                            goal_check = "YES"
                        elif "NO" in clean_resp or "NOT FOUND" in clean_resp or "NOT VISIBLE" in clean_resp: 
                            goal_check = "NO"
                        elif "CLEAR" in clean_resp:
                            goal_check = "CLEAR"
                        elif "BLOCKED" in clean_resp:
                            goal_check = "BLOCKED"
                    
                    # Force goal_check to YES if a bounding box is found to ensure robust state machine flow
                    if parsed_box is not None:
                        goal_check = "YES"
                    
                    # These matches are only needed if the VLM provides them (usually structured mode)
                    plan_match = re.search(r'Plan:\s*(.*?)(?=\n*(?:Reasoning|<cmd>|<box>)|$)', response, re.IGNORECASE | re.DOTALL)
                    reasoning_match = re.search(r'Reasoning:\s*(.*?)(?=\n*(?:<cmd>|<box>)|$)', response, re.IGNORECASE | re.DOTALL)
                    
                    plan = plan_match.group(1).strip() if plan_match else "No plan provided."
                    reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided."
                    cmd = cmd_match.group(1).strip() if cmd_match else "NONE"
                    
                    # Stream the prompt for the 'Show Full Prompt' feature
                    yield self.format_sse('prompt_update', prompt)
 
                    # Stream the reasoning/response immediately so the user sees it
                    yield self.format_sse('reasoning_chunk', f"VLM Output: {goal_check.capitalize()}<br>")
 
                # Handle State Transitions and Optimized Search Logic (SEARCHING only)
                if self.state == "SEARCHING":
                    if goal_check.upper() == "YES" or parsed_box is not None:
                        self.state = "FINDING"
                        yield self.format_sse('log', "Goal confirmed by VLM. Switching to FINDING mode.")
                        continue # Re-evaluate state at top of loop for FINDING prompt
                    elif goal_check.upper() == "NO":
                        yield self.format_sse('log', "Goal not found. Executing smooth autonomous 90-degree search turn...")
                        
                        # 1. Execute Move Smoothly (9 steps of 10 degrees for realistic neck-turning)
                        if self.execute_cmds:
                            try:
                                yield self.format_sse('log', "Initiating smooth 90-degree environmental scan...")
                                for i in range(9):
                                    if self.collision_flag:
                                        break
                                    # Use the 10-degree 'turn_right' action
                                    move_res = await self.move_callback("turn_right")
                                    if move_res:
                                        yield self.format_sse('frame_update', move_res)
                                    if self.collision_flag:
                                        break
                                    # 0.3s delay makes it look like a human turning their head (slightly faster)
                                    await asyncio.sleep(0.3)
                                
                                if self.collision_flag:
                                    if self.state == "RECOVERING":
                                        self.state = "SEARCHING"
                                        self.collision_flag = False
                                    else:
                                        self.state = "RECOVERING"
                                    continue
                                
                                yield self.format_sse('log', "Environmental scan (90°) completed.")
                            except Exception as e:
                                yield self.format_sse('error', f"Search turn failed: {e}")
                        
                        # 2. Provide result feedback to UI result display
                        yield self.format_sse('reasoning_chunk', f"<b>Searching...</b> (90° Scan complete - No door found)<br>")
                        
                        # Update memory so next reasoning knows we just turned
                        self.memory.append(f"[Turn 90 Degrees Right] (State: SEARCHING) - Goal not found, scanning next 90 degrees.")

                        # 3. Stabilize and Continue
                        await asyncio.sleep(0.5) 
                        yield self.format_sse('log', "Starting next analysis step automatically...")
                        continue # RESTART LOOP IMMEDIATELY FOR NEXT VIEW
                
                # Action Logic (Internal state management continues)
                safe_cmd = cmd.lower()
                if safe_cmd == "task completed":
                    yield self.format_sse('log', "Task Completed! Stopping navigation.")
                    self._is_running = False
                    break
                    
                habitat_cmd = self.cmd_map.get(safe_cmd)
                
                if habitat_cmd:
                    # Update memory
                    self.memory.append(f"[{cmd}] (State: {self.state}) - {reasoning}")
                    
                    if self.execute_cmds:
                        try:
                            # Smoothing for large turns to create human-like effect
                            if "turn" in habitat_cmd and "_" in habitat_cmd:
                                # Extract degrees: turn_left_30 -> 30
                                parts = habitat_cmd.split('_')
                                if len(parts) == 3 and parts[2].isdigit():
                                    degrees = int(parts[2])
                                    base_dir = f"{parts[0]}_{parts[1]}" # turn_left
                                    steps = degrees // 10
                                    remainder = degrees % 10
                                    
                                    yield self.format_sse('log', f"Executing smooth rotation: {degrees} degrees ({steps} steps)...")
                                    for i in range(steps):
                                        if not self._is_running or self.collision_flag:
                                            break
                                        move_res = await self.move_callback(base_dir)
                                        if move_res:
                                            yield self.format_sse('frame_update', move_res)
                                        if not self._is_running or self.collision_flag:
                                            break
                                        await asyncio.sleep(0.5)
                                    
                                    if remainder > 0 and not self.collision_flag:
                                        # Fallback for odd angles if we ever add them
                                        await self.move_callback(habitat_cmd)
                                else:
                                    # Fallback for turn_left/right (standard 10 deg)
                                    move_res = await self.move_callback(habitat_cmd)
                                    if move_res: yield self.format_sse('frame_update', move_res)
                            else:
                                # Standard move or 10-deg turn
                                yield self.format_sse('log', f"Executing action: {habitat_cmd} ({cmd})")
                                move_res = await self.move_callback(habitat_cmd)
                                if move_res:
                                     yield self.format_sse('frame_update', move_res)
                                     
                            if self.collision_flag:
                                if self.state == "RECOVERING":
                                    yield self.format_sse('log', "Collision during recovery. Adjusting to SEARCHING to break loop.")
                                    self.state = "SEARCHING"
                                    self.collision_flag = False
                                else:
                                    self.state = "RECOVERING"
                                continue
                        except Exception as e:
                            yield self.format_sse('error', f"Movement failed: {str(e)}")
                    else:
                        yield self.format_sse('log', f"Suggested action (not executed): {cmd}")
                else:
                    if not hasattr(self, '_none_cmd_count'): self._none_cmd_count = 0
                    
                    if cmd != "NONE":
                        yield self.format_sse('log', f"[System] Invalid or missing command: {cmd}")
                        self._none_cmd_count = 0
                    else:
                        self._none_cmd_count += 1
                        yield self.format_sse('log', f"[System] No command provided by VLM. (Attempt {self._none_cmd_count}/3)")
                        
                        if self._none_cmd_count >= 3:
                            yield self.format_sse('error', "Stuck in empty command loop. Stopping navigation for safety.")
                            self._is_running = False
                            break
                
                await asyncio.sleep(0.2) # Faster iterations for state machine responsiveness
                
            yield self.format_sse('log', 'Autonomous Navigation stopped.')
            yield self.format_sse('stopped', True)
        finally:
            self._streaming_active = False
            self._is_running = False

    def _b64_to_cv2(self, b64_string):
        """Utility to convert base64 frame to CV2 image."""
        img_data = base64.b64decode(b64_string)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
