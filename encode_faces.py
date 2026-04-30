import face_recognition
import pickle
import os

dataset_path = "dataset"
encoding_file = "encodings/encodings.pkl"

known_encodings = []
known_names = []

print("[INFO] Encoding faces...")

for student_name in os.listdir(dataset_path):
    student_folder = os.path.join(dataset_path, student_name)

    if not os.path.isdir(student_folder):
        continue

    for img_name in os.listdir(student_folder):
        img_path = os.path.join(student_folder, img_name)

        img = face_recognition.load_image_file(img_path)
        boxes = face_recognition.face_locations(img)

        if len(boxes) == 0:
            print(f"[WARNING] No face found: {img_path}")
            continue

        encoding = face_recognition.face_encodings(img, boxes)[0]

        known_encodings.append(encoding)
        known_names.append(student_name)

data = {
    "encodings": known_encodings,
    "names": known_names
}

os.makedirs("encodings", exist_ok=True)

with open(encoding_file, "wb") as f:
    pickle.dump(data, f)

print("[INFO] Encodings saved to encodings.pkl")
