import os
import sys
import tarfile
import shutil
import tempfile

def check_and_extract_habitats(project_root):
    habitats_dir = os.path.join(project_root, "habitats")
    if not os.path.exists(habitats_dir):
        os.makedirs(habitats_dir)
        return

    # Find tar files
    tar_files = [f for f in os.listdir(habitats_dir) if f.endswith(".tar")]
    
    for tar_filename in tar_files:
        tar_path = os.path.join(habitats_dir, tar_filename)
        print(f"[*] Found habitat archive: {tar_filename}. Extracting...")
        
        with tempfile.TemporaryDirectory(dir=habitats_dir) as tmpdirname:
            try:
                with tarfile.open(tar_path, "r") as tar:
                    tar.extractall(path=tmpdirname)
                
                # Move .glb and .json files to root of habitats
                extracted_count = 0
                for root, dirs, files in os.walk(tmpdirname):
                    for file in files:
                        if file.endswith(".glb") or file.endswith(".json"):
                            src_path = os.path.join(root, file)
                            dst_path = os.path.join(habitats_dir, file)
                            
                            # Handle name collisions
                            if os.path.exists(dst_path):
                                base, ext = os.path.splitext(file)
                                count = 1
                                while os.path.exists(dst_path):
                                    dst_path = os.path.join(habitats_dir, f"{base}_{count}{ext}")
                                    count += 1
                                    
                            shutil.move(src_path, dst_path)
                            extracted_count += 1
                
                print(f"[+] Successfully extracted {extracted_count} map files from {tar_filename}.")
                
                # Delete the original tar file
                os.remove(tar_path)
                print(f"[+] Deleted archive {tar_filename} to save space.")
                
            except Exception as e:
                print(f"[!] Error extracting {tar_filename}: {e}")

def check_models(project_root):
    models_dir = os.path.join(project_root, "models")
    
    required_models = [
        ("Segmentation", "sam2.1-hiera-tiny"),
        ("Vision Foundation", "GroundingDINO-main"),
        ("Vision Language", "Qwen3.5-VL-0.8B")
    ]
    
    missing_models = []
    
    for category, model_name in required_models:
        model_path = os.path.join(models_dir, category, model_name)
        if not os.path.exists(model_path) or not os.listdir(model_path):
            missing_models.append(os.path.join("models", category, model_name))
            
    if missing_models:
        print("\n" + "="*60)
        print("[WARNING] MISSING REQUIRED MODELS!")
        print("The following models were not found in your directory:")
        for m in missing_models:
            print(f"  - {m}")
        print("\nPlease check the README.md for download instructions.")
        print("="*60 + "\n")
    else:
        print("[+] All required models found.")

if __name__ == "__main__":
    # Run relative to project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    check_and_extract_habitats(project_root)
    check_models(project_root)
