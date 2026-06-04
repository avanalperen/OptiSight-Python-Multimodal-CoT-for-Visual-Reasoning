import habitat_sim
import numpy as np
import magnum as mn

def main():
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_id = "test habitats/skokloster-castle.glb"
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [habitat_sim.CameraSensorSpec()]
    agent_cfg.sensor_specifications[0].uuid = "color_sensor"
    agent_cfg.sensor_specifications[0].sensor_type = habitat_sim.SensorType.COLOR
    
    cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
    sim = habitat_sim.Simulator(cfg)
    agent = sim.initialize_agent(0)
    
    sensor_node = agent.scene_node.node_sensor_suite.get("color_sensor").node
    
    print("Initial rotation:", sensor_node.rotation)
    
    agent.act("look_down")
    print("After look_down (10 deg):", sensor_node.rotation)
    
    agent.act("look_down")
    print("After second look_down (20 deg):", sensor_node.rotation)
    
    agent.act("look_up")
    print("After look_up:", sensor_node.rotation)
    
    sim.close()

if __name__ == "__main__":
    main()
