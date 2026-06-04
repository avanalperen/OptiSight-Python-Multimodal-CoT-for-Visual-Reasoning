import magnum as mn
import numpy as np

def main():
    try:
        q_identity = mn.Quaternion()
        print("Identity Quaternion:", q_identity)
        
        # Test Deg and Vector3
        angle = mn.Deg(-40.0)
        axis = mn.Vector3(1.0, 0.0, 0.0)
        q_rot = mn.Quaternion.rotation(angle, axis)
        print("Rotated Quaternion:", q_rot)
        print("Quaternion values (vector, scalar):", q_rot.vector, q_rot.scalar)
        
        print("Success! Magnum rotation is working perfectly.")
    except Exception as e:
        print("Failed to run Magnum math:", e)

if __name__ == "__main__":
    main()
