import numpy as np

def project_test():
    # Habitat Defaults
    height, width = 1080, 1920
    hfov = 90.0
    hfov_rad = np.deg2rad(hfov)
    
    # Intrinsics
    cx = width / 2.0
    cy = height / 2.0
    fx = (width / 2.0) / np.tan(hfov_rad / 2.0)
    fy = fx
    
    # Given a 2D point (u,v) and depth d
    u, v = width * 0.2, height * 0.8
    d = 5.0 # meters
    
    # 2D to 3D Camera Local
    # Habitat uses -Z forward, Y up, X right
    x_c = (u - cx) * d / fx
    y_c = (cy - v) * d / fy # Habitat image Y is down, camera Y is up
    z_c = -d
    
    camera_point = np.array([x_c, y_c, z_c, 1.0])
    
    print("Camera Point:", camera_point)
    
    # Camera to 2D
    # z_c must be negative
    z_c_clip = max(-z_c, 1e-5) # distance in front of camera
    u_proj = (x_c * fx / z_c_clip) + cx
    v_proj = cy - (y_c * fy / z_c_clip)
    
    print("Projected Point:", (u_proj, v_proj))
    print("Original Point:", (u, v))

if __name__ == "__main__":
    project_test()
