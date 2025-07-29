import os
import cv2
import glob
import json
import shutil
import numpy as np
from insightface.app import FaceAnalysis
from ultralytics import YOLO

# Load Setting
with open("setting.json", "r", encoding="utf-8") as cf:
    setting = json.load(cf)

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

model_path = config.get("model_path")
confidence_threshold = setting.get("confidence_threshold")
bounding_box_size = setting.get("bounding_box_size")
similarity_upper = setting.get("similarity_upper")
similarity_lower = setting.get("similarity_lower")
similarity_step = setting.get("similarity_step")

# Initialize Models
face_app = FaceAnalysis(name="antelopev2", root="./", providers=['CUDAExecutionProvider'])
face_app.prepare(ctx_id=0)

model = YOLO(model_path)
model.to("cuda")

# Load Targets List
with open("targets.json", "r", encoding="utf-8") as f:
    targets = json.load(f)

print("Select a Target to Self-Train:")
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

def average_embeddings(folder):
    embeddings = []
    for img_path in glob.glob(os.path.join(folder, "*")):
        img = cv2.imread(img_path)
        if img is None:
            continue
        faces = face_app.get(img)
        for face in faces:
            embeddings.append(face.normed_embedding)
    if not embeddings:
        return None
    return np.mean(embeddings, axis=0)  # Average embedding

def test_output(img):
    results = model.predict(source=img, imgsz=640, conf=0.25, iou=0.45, verbose=False)
    r = results[0]

    person_boxes = [(cls, score, box) for cls, score, box in zip(r.boxes.cls, r.boxes.conf, r.boxes.xyxy) if int(cls) == 0]
    person_count = len(person_boxes)

    is_single = person_count == 1

    passed_test = False
    for cls, score, box in person_boxes:
        if float(score) >= confidence_threshold:
            x1, y1, x2, y2 = box
            area = float((x2 - x1) * (y2 - y1))
            if area >= bounding_box_size:
                passed_test = True
                break

    return is_single, passed_test

def self_train_user(user):
    detected_dir = os.path.join("output", user, "detected")
    single_dir = os.path.join("output", user, "single")
    multiple_dir = os.path.join("output", user, "multiple")
    ambiguous_dir = os.path.join("output", user, "ambiguous")
    unmatched_dir = os.path.join("output", user, "unmatched")

    for d in [single_dir, multiple_dir, ambiguous_dir, unmatched_dir]:
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(detected_dir):
        print(f"[{user}] Missing Detected Folder")
        return

    print(f"\nSelf-training for User: {user}")
    threshold = similarity_upper
    used_images = set()

    while True:
        print(f"\nCurrent Similarity Threshold: {threshold:.2f}")
        center_embedding = average_embeddings(single_dir)
        if center_embedding is None:
            print("No Embeddings Found, Skipping")
            return

        new_matches = 0

        for img_path in glob.glob(os.path.join(detected_dir, "*")):
            filename = os.path.basename(img_path)
            if filename in used_images:
                continue

            img = cv2.imread(img_path)
            if img is None:
                continue

            faces = face_app.get(img)
            matched = False
            for face in faces:
                emb = face.normed_embedding
                similarity = np.dot(center_embedding, emb)
                if similarity > threshold:
                    matched = True
                    break

            if not matched:
                continue

            used_images.add(filename)
            is_single, passed_test = test_output(img)

            if is_single:
                if passed_test:
                    shutil.copy(img_path, os.path.join(single_dir, filename))
                    new_matches += 1
                else:
                    shutil.copy(img_path, os.path.join(ambiguous_dir, filename))
            else:
                shutil.copy(img_path, os.path.join(multiple_dir, filename))

        print(f"Matched {new_matches} Images")

        if threshold <= similarity_lower and new_matches == 0:
            break

        if threshold > similarity_lower:
            threshold = max(threshold - similarity_step, similarity_lower)

    # Final Unmatched Handling
    for img_path in glob.glob(os.path.join(detected_dir, "*")):
        filename = os.path.basename(img_path)
        if filename not in used_images:
            shutil.copy(img_path, os.path.join(unmatched_dir, filename))

    print(f"\nFinished for {user}")

for user in selected_users:
    self_train_user(user)
