import numpy as np
import habitat_sim

def test_proj_with_transform():
    # Setup sim to verify
    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_id = "test habitats/skokloster-castle.glb"
    
    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [habitat_sim.CameraSensorSpec(), habitat_sim.CameraSensorSpec()]
    agent_cfg.sensor_specifications[1].uuid = "depth_sensor"
    agent_cfg.sensor_specifications[1].sensor_type = habitat_sim.SensorType.DEPTH
    
    cfg = habitat_sim.Configuration(sim_cfg, [agent_cfg])
    sim = habitat_sim.Simulator(cfg)
    agent = sim.initialize_agent(0)
    
    sensor_node = agent.scene_node.node_sensor_suite.get("color_sensor").node
    T_wc = np.array(sensor_node.absolute_transformation())
    
    print("T_wc:", T_wc)
    
    # Rest of math
    u, v = 384.0, 864.0
    d = 5.0
    cx, cy, fx, fy = 1920/2, 1080/2, 960.0, 960.0
    
    x_c = (u - cx) * d / fx
    y_c = (cy - v) * d / fy
    z_c = -d
    
    P_c = np.array([x_c, y_c, z_c, 1.0])
    P_w = T_wc @ P_c
    print("World Point:", P_w)
    
    # Move Agent
    agent.act("turn_right")
    
    # Reproject
    T_wc_new = np.array(sensor_node.absolute_transformation())
    T_cw_new = np.linalg.inv(T_wc_new)
    
    P_c_new = T_cw_new @ P_w
    
    # Avoid division by zero
    z_dist = -P_c_new[2]
    if z_dist > 1e-5:
        u_new = (P_c_new[0] * fx / z_dist) + cx
        v_new = cy - (P_c_new[1] * fy / z_dist)
        print("New projected point:", u_new, v_new)
    else:
        print("Point is behind camera")
        
    sim.close()

if __name__ == "__main__":
    test_proj_with_transform()
