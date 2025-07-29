import os
import subprocess
import sys
import shutil
import platform
import requests
import zipfile

ENVIRONMENT = "InstagramCollector"
VERSION = "3.10"
PACKAGES = [
    "opencv-python",
    "numpy",
    "insightface",
    "ultralytics",
    "instagrapi",
    "python-dotenv",
    "requests"
]

def run_cmd(cmd, desc=None):
    if desc:
        print(f"\n[INFO] {desc}")
    print(f"[Run] {cmd}")
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in process.stdout:
        print(line, end='')
    process.wait()
    if process.returncode != 0:
        print(f"Failed：{cmd}")
        sys.exit(1)

def conda_exists():
    return shutil.which("conda") is not None

def has_gpu():
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

def get_activate_cmd(env_name):
    if platform.system() == "Windows":
        return f'conda activate {env_name} &&'
    else:  # Linux / macOS
        return f'source activate {env_name} &&'

def download_models():
    model_path = "./models"
    os.makedirs(model_path, exist_ok=True)

    # YOLO
    yolo_path = os.path.join(model_path, "yolo11m.pt")
    with requests.get("https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11m.pt", stream=True) as r:
        r.raise_for_status()
        with open(yolo_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    # Antelopev2
    antelope_zip = os.path.join(model_path, "antelopev2.zip")
    with requests.get("https://github.com/deepinsight/insightface/releases/download/v0.7/antelopev2.zip", stream=True) as r:
        r.raise_for_status()
        with open(antelope_zip, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    with zipfile.ZipFile(antelope_zip, 'r') as zip_ref:
        zip_ref.extractall(os.path.join(model_path, "antelopev2"))




def main():
    if not conda_exists():
        print("Please Install Anaconda or Miniconda First")
        sys.exit(1)

    run_cmd(f"conda create -y -n {ENVIRONMENT} python={VERSION}", desc="[INFO] Creating Conda Environment...")

    print("\n[INFO] GPU Detecting...")
    gpu_flag = "onnxruntime-gpu" if has_gpu() else "onnxruntime"
    full_packages = " ".join(PACKAGES + [gpu_flag])

    activate_cmd = get_activate_cmd(ENVIRONMENT)
    run_cmd(f'{activate_cmd} pip install {full_packages}', desc="[INFO] Installing Dependencies...")

    print(f"\n[INFO] Environment '{ENVIRONMENT}' Setup Completed")

if __name__ == "__main__":
    main()
    download_models()