import os
import json
import shutil
from ultralytics import YOLO

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

model_path = config.get("model_path")
threshold = config.get("threshold")
target_class = config.get("target_class")

with open("targets.json", "r", encoding="utf-8") as f:
    targets = json.load(f)

model = YOLO(model_path)
model.to("cuda")

print("Select a Target to Detect:")
print("0. All")
for idx, user in enumerate(targets, start=1):
    print(f"{idx}. {user}")

choice = input("Enter the Number Correspondingly: ").strip()
if choice == "0":
    selected_users = targets
else:
    try:
        selected_users = [targets[int(choice) - 1]]
    except (IndexError, ValueError):
        print("Invalid Selection")
        exit(1)

image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')

def detection(image_path, root, input_folder, detected_dir, missed_dir):
    try:
        results = model(image_path)[0]
        detected = False

        for box in results.boxes:
            cls = int(box.cls)
            conf = float(box.conf)
            if results.names[cls] == target_class and conf > threshold:
                rel_path = os.path.relpath(root, input_folder)
                prefix = rel_path.replace(os.sep, "_") if rel_path not in (".", "") else ""
                basename = os.path.basename(image_path)
                new_filename = f"{prefix}_{basename}" if prefix else basename
                detected_path = os.path.join(detected_dir, new_filename)
                shutil.copy2(image_path, detected_path)
                detected = True
                break

        if not detected:
            rel_path = os.path.relpath(root, input_folder)
            prefix = rel_path.replace(os.sep, "_") if rel_path not in (".", "") else ""
            basename = os.path.basename(image_path)
            new_filename = f"{prefix}_{basename}" if prefix else basename
            missed_path = os.path.join(missed_dir, new_filename)
            shutil.copy2(image_path, missed_path)

    except Exception as e:
        print(f"Skipped {os.path.basename(image_path)} Due to Error: {e}")

for user in selected_users:
    input_folder = os.path.abspath(os.path.join("data", user))
    print(f"\nProcessing Folder: {input_folder}")

    output_base = os.path.abspath("output")
    detected_dir = os.path.join(output_base, user, "detected")
    missed_dir = os.path.join(output_base, user, "missed")
    os.makedirs(detected_dir, exist_ok=True)
    os.makedirs(missed_dir, exist_ok=True)

    for root, _, files in os.walk(input_folder):
        for filename in files:
            if filename.lower().endswith(image_extensions):
                image_path = os.path.join(root, filename)
                detection(image_path, root, input_folder, detected_dir, missed_dir)
