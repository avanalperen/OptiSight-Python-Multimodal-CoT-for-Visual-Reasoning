import os
import sys
import subprocess

def main():
    # Find the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Set the working directory to the project root
    os.chdir(project_root)
    
    # Determine the path to server.py
    server_script = os.path.join(project_root, "codes", "server.py")
    
    if not os.path.exists(server_script):
        print(f"Error: {server_script} not found.")
        sys.exit(1)
        
    print(f"Starting the server... (Root Directory: {project_root})")
    
    try:
        # Run the resource checker first
        checker_script = os.path.join(project_root, "codes", "check_resources.py")
        if os.path.exists(checker_script):
            subprocess.run([sys.executable, "-B", checker_script])
        
        # Run server.py using the current Python (or Conda) environment without generating __pycache__
        subprocess.run([sys.executable, "-B", server_script])
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
