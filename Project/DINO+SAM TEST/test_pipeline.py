import sys
import os
import cv2
import numpy as np
from PIL import Image
import torch

# Add the path where Grounded-SAM pipeline resides
# Use WSL paths as we are running in WSL
GD_PATH = "/mnt/c/Alperen/IRI Internship/Open-Vocabulary Object Detectors/GroundingDINO-main"
if GD_PATH not in sys.path:
    sys.path.append(GD_PATH)

try:
    from grounded_sam_pipeline import GroundedSAM
    import supervision as sv
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    sys.exit(1)

def run_test():
    # Use WSL paths as we are running in WSL
    test_dir = "/mnt/c/Alperen/IRI Internship/My Project/Project/DINO+SAM TEST"
    input_path = os.path.join(test_dir, "Example Input.jpg")
    text_path = os.path.join(test_dir, "Text Input.txt")
    
    if not os.path.exists(input_path):
        print(f"Error: Input image not found at {input_path}")
        return

    with open(text_path, "r") as f:
        text_prompt = f.read().strip()
    
    print(f"--- Isolated Grounded-SAM Test ---")
    print(f"Input: {input_path}")
    print(f"Prompt: '{text_prompt}'")
    
    # Initialize pipeline
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    # Initialize pipeline with absolute paths
    try:
        # Construct WSL-friendly paths
        gd_config = os.path.join(GD_PATH, "groundingdino/config/GroundingDINO_SwinT_OGC.py")
        gd_weights = os.path.join(GD_PATH, "groundingdino_swint_ogc.pth")
        sam2_path = "/mnt/c/Alperen/IRI Internship/Vision Foundation Models/sam2.1-hiera-tiny"
        
        pipeline = GroundedSAM(
            gd_config_path=gd_config,
            gd_weights_path=gd_weights,
            sam2_path=sam2_path,
            device=device
        )
    except Exception as e:
        print(f"Failed to initialize GroundedSAM: {e}")
        return
    
    # Load image
    image_pil = Image.open(input_path).convert("RGB")
    image_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
    
    # Run prediction
    print("Executing Grounding DINO + SAM 2.1 pipeline...")
    try:
        detections = pipeline.predict(image_pil, text_prompt=text_prompt)
    except Exception as e:
        import traceback
        print(f"Pipeline execution failed: {e}")
        traceback.print_exc()
        return
        
    print(f"Analysis Complete. Objects found: {len(detections.xyxy)}")
    
    if len(detections.xyxy) > 0:
        # Create output annotators
        box_annotator = sv.BoxAnnotator()
        mask_annotator = sv.MaskAnnotator()
        
        # 1. Generate DINO Output (Boxes only)
        dino_frame = box_annotator.annotate(scene=image_cv.copy(), detections=detections)
        dino_path = os.path.join(test_dir, "1_DINO_OUTPUT.jpg")
        cv2.imwrite(dino_path, dino_frame)
        print(f"SUCCESS: 1_DINO_OUTPUT.jpg generated.")
        
        # 2. Generate SAM Output (Masks + Boxes)
        # We use the dino_frame as base to show both boxes and masks
        sam_frame = mask_annotator.annotate(scene=dino_frame.copy(), detections=detections)
        sam_path = os.path.join(test_dir, "2_SAM_OUTPUT.jpg")
        cv2.imwrite(sam_path, sam_frame)
        print(f"SUCCESS: 2_SAM_OUTPUT.jpg generated.")
        
        # Print detection details
        for i in range(len(detections.xyxy)):
            box = detections.xyxy[i]
            conf = detections.confidence[i]
            print(f" - Match {i+1}: Box=[{int(box[0])}, {int(box[1])}, {int(box[2])}, {int(box[3])}], Confidence={conf:.2f}")
    else:
        print("RESULT: No objects detected matching the prompt.")

if __name__ == "__main__":
    run_test()
