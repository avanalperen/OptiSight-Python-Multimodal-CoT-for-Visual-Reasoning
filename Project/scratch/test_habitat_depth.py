import sys
import os
import numpy as np

# Mocking habitat-sim if running in windows, but I'll run this in wsl
import habitat_sim

def main():
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_id = "test habitats/skokloster-castle.glb"
    
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [
        habitat_sim.CameraSensorSpec(),
        habitat_sim.CameraSensorSpec()
    ]
    agent_cfg.sensor_specifications[0].uuid = "color_sensor"
    agent_cfg.sensor_specifications[0].sensor_type = habitat_sim.SensorType.COLOR
    agent_cfg.sensor_specifications[0].resolution = [1080, 1920]
    
    agent_cfg.sensor_specifications[1].uuid = "depth_sensor"
    agent_cfg.sensor_specifications[1].sensor_type = habitat_sim.SensorType.DEPTH
    agent_cfg.sensor_specifications[1].resolution = [1080, 1920]
    agent_cfg.sensor_specifications[1].far = 1000.0
    
    cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
    sim = habitat_sim.Simulator(cfg)
    agent = sim.initialize_agent(0)
    
    obs = sim.get_sensor_observations()
    depth = obs.get("depth_sensor")
    print(f"Depth max: {np.max(depth)}, min: {np.min(depth)}")
    print(f"Center pixel depth: {depth[540, 960]}")
    
    # Test matrix
    sensor_node = agent.scene_node.node_sensor_suite.get("color_sensor").node
    T_wc = np.array(sensor_node.absolute_transformation())
    print("T_wc shape:", T_wc.shape)
    print("T_wc type:", type(T_wc))
    print(T_wc)

if __name__ == "__main__":
    main()
