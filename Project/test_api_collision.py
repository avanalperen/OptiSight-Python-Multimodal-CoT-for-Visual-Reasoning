import requests
import time

url = "http://localhost:8000"

# Init sim
print("Initializing SIM...")
res = requests.post(f"{url}/init_sim", data={"scene_name": "skokloster-castle.glb"})
print(res.json())

time.sleep(1)

collided = False
for i in range(50):
    res = requests.post(f"{url}/move", data={"command": "move_forward"})
    data = res.json()
    collisions = data.get("collisions", 0)
    print(f"Step {i}, Collisions: {collisions}")
    if collisions > 0:
        collided = True
        print("Collision counter effectively works!")
        break

if not collided:
    print("Could not trigger a collision within 50 steps.")
