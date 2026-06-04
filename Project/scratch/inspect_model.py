import torch
from transformers import AutoModelForMultimodalLM, AutoProcessor
import inspect
import sys
import os

model_path = "/mnt/c/Alperen/IRI Internship/Vision Language Models/Qwen3.5-VL-2B"
if not os.path.exists(model_path):
    model_path = "c:/Alperen/IRI Internship/Vision Language Models/Qwen3.5-VL-2B"

print(f"Checking model at: {model_path} with AutoModelForMultimodalLM")
try:
    model = AutoModelForMultimodalLM.from_pretrained(
        model_path, 
        trust_remote_code=True, 
        device_map="cpu",
        torch_dtype=torch.float32
    )
    print("Class Name:", model.__class__.__name__)
    print("Forward Signature:", inspect.signature(model.forward))
    print("Has visual component:", hasattr(model, "visual"))
except Exception as e:
    print("Error loading model:", e)
