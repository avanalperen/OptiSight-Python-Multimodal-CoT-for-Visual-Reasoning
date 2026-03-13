import time
import re
import json
import logging
from collections import deque

logger = logging.getLogger(__name__)

class AutonomousNavigator:
    def __init__(self, inference_callback, move_callback, execute_cmds=True):
        self.inference_callback = inference_callback
        self.move_callback = move_callback
        self.execute_cmds = execute_cmds
        
        self.goal = ""
        self.state = "SEARCHING" # [SEARCHING, NAVIGATING, RECOVERING]
        self.memory = deque(maxlen=2)
        self.collision_flag = False
        
        # Default templates
        self.prompts = {
            "core": "", # Base template if needed, though we'll likely use 3 others
            "searching": """You are the OptiSight Visual Reasoning Core (SEARCHING MODE).
GOAL: {goal}
STATE: SEARCHING (Look for the goal)
MEMORY: {memory}

[INSTRUCTIONS]
1. Scan the environment. Path availability?
2. Move to explore. Look for the goal.
3. strictly 1 sentence reasoning. output <cmd>COMMAND</cmd>.
Valid: <cmd>Go Ahead</cmd>, <cmd>Turn Left</cmd>, <cmd>Turn Right</cmd>, <cmd>Turn Back</cmd>, <cmd>Task Completed</cmd>.

Output Format:
Observation: (Max 15 words)
Goal_Check: (YES/NO)
Plan: (2 sub-steps)
Reasoning: (1 sentence)
<cmd>COMMAND</cmd>""",
            "navigating": """You are the OptiSight Visual Reasoning Core (NAVIGATING MODE).
GOAL: {goal}
STATE: NAVIGATING (Goal in Sight)
MEMORY: {memory}

[INSTRUCTIONS]
1. Goal is visible! Align with it.
2. Advance toward the goal. Avoid obstacles.
3. strictly 1 sentence reasoning. output <cmd>COMMAND</cmd>.

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
            "turn back": "move_backward",
            "task completed": "stop"
        }
        self._is_running = False

    def update_settings(self, goal, prompts=None, initial_state="SEARCHING"):
        self.goal = goal
        self.state = initial_state
        if prompts:
            self.prompts.update(prompts)
        self.memory.clear()
        
    def set_running(self, state: bool):
        self._is_running = state

    def trigger_collision(self):
        """External call to flag a collision for the next iteration."""
        self.collision_flag = True

    def format_sse(self, event_type, data):
        """Format data as Server-Sent Events"""
        if isinstance(data, str):
            data = data.replace('\n', ' ')
        payload = json.dumps({'type': event_type, 'data': data})
        return f"data: {payload}\n\n"

    def navigate_stream(self):
        """Generator function for Flask/FastAPI SSE streaming."""
        self._is_running = True
        logger.info(f"Autonomous Navigation started in state: {self.state}")
        
        yield self.format_sse('log', f"Started OptiSight Core targeting: {self.goal}")
        
        while self._is_running:
            # Check for external collision trigger
            if self.collision_flag:
                logger.warning("Collision detected! Switching to RECOVERING state.")
                self.state = "RECOVERING"
                self.collision_flag = False
                yield self.format_sse('log', "[System] Collision detected! Entering Recovery Mode.")

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
            
            # Merge Core + State templates
            full_template = core_template + "\n\n" + state_template if core_template else state_template
            
            prompt = full_template.replace("{goal}", self.goal).replace("{memory}", mem_str).replace("{state}", self.state)
            
            yield self.format_sse('state_update', {"state": self.state})
            yield self.format_sse('log', f"Analyzing scene (State: {self.state})...")
            
            # 1. Call Inference
            try:
                response = self.inference_callback(prompt)
            except Exception as e:
                yield self.format_sse('error', f"Inference failed: {str(e)}")
                self._is_running = False
                break
                
            if not self._is_running:
                break
                
            # 2. Parse Response
            obs_match = re.search(r'Observation:\s*(.*?)(?=\n*Goal_Check:|$)', response, re.IGNORECASE | re.DOTALL)
            goal_match = re.search(r'Goal_Check:\s*(.*?)(?=\n*Plan:|$)', response, re.IGNORECASE)
            plan_match = re.search(r'Plan:\s*(.*?)(?=\n*Reasoning:|$)', response, re.IGNORECASE | re.DOTALL)
            reasoning_match = re.search(r'Reasoning:\s*(.*?)(?=\n*<cmd>|$)', response, re.IGNORECASE | re.DOTALL)
            cmd_match = re.search(r'<cmd>(.*?)</cmd>', response, re.IGNORECASE)
            
            observation = obs_match.group(1).strip() if obs_match else "No observation"
            goal_check = goal_match.group(1).strip() if goal_match else "UNKNOWN"
            plan = plan_match.group(1).strip() if plan_match else "No plan provided."
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided."
            cmd = cmd_match.group(1).strip() if cmd_match else "NONE"
            
            # Handle State Transitions based on VLM output
            if self.state == "SEARCHING" and goal_check.upper() == "YES":
                self.state = "NAVIGATING"
                yield self.format_sse('log', "Goal spotted! Transitioning to NAVIGATING.")
            elif self.state == "RECOVERING":
                # In recovery, we check if center is now clear
                if "clear" in observation.lower() and "center" in observation.lower():
                    self.state = "SEARCHING"
                    yield self.format_sse('log', "Path cleared. Returning to SEARCHING.")

            # Stream the parsed components to the UI
            yield self.format_sse('reasoning_chunk', f"<b>Observation:</b> {observation}<br>")
            time.sleep(0.05)
            yield self.format_sse('reasoning_chunk', f"<b>Goal Check:</b> {goal_check}<br>")
            time.sleep(0.05)
            
            # Stream Plan
            yield self.format_sse('reasoning_chunk', f"<b>Plan:</b> {plan}<br>")
            time.sleep(0.05)

            # Stream reasoning sentence by sentence for effect
            yield self.format_sse('reasoning_chunk', "<b>Reasoning:</b> ")
            sentences = re.split(r'(?<=[.!?])\s+', reasoning)
            for sentence in sentences:
                if sentence:
                    yield self.format_sse('reasoning_chunk', sentence.strip() + " ")
                    time.sleep(0.1)
                    
            yield self.format_sse('reasoning_chunk', f"<br><b>Command:</b> &lt;cmd&gt;{cmd}&lt;/cmd&gt;")
            
            # 3. Action Logic
            safe_cmd = cmd.lower()
            if safe_cmd == "task completed":
                yield self.format_sse('log', "Task Completed! Stopping navigation.")
                self._is_running = False
                break
                
            habitat_cmd = self.cmd_map.get(safe_cmd)
            
            if habitat_cmd:
                # Update memory
                self.memory.append(f"[{cmd}] - {reasoning}")
                
                if self.execute_cmds:
                    yield self.format_sse('log', f"Executing action: {habitat_cmd} ({cmd})")
                    try:
                        cmd_result = self.move_callback(habitat_cmd)
                        if cmd_result:
                             yield self.format_sse('frame_update', cmd_result)
                    except Exception as e:
                        yield self.format_sse('error', f"Movement failed: {str(e)}")
                else:
                    yield self.format_sse('log', f"Suggested action (not executed): {cmd}")
            else:
                 yield self.format_sse('log', f"Invalid or missing command: {cmd}")
            
            time.sleep(0.2) # Faster iterations for state machine responsiveness
            
        yield self.format_sse('log', 'Autonomous Navigation stopped.')
        yield self.format_sse('stopped', True)
