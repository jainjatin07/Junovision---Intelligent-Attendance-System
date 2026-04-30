import cv2
import pickle
import pandas as pd
from datetime import datetime
import os

encoding_file = "encodings/encodings.pkl"

def mark_attendance(image_path):
    try:
        import face_recognition
        import numpy as np

        # Check encoding file
        if not os.path.exists(encoding_file):
            print("Encoding file not found!")
            return [], "error.csv"

        with open(encoding_file, "rb") as f:
            data = pickle.load(f)

        known_encodings = data["encodings"]
        known_names = data["names"]

        # Load image
        img = cv2.imread(image_path)
        if img is None:
            print("Image not loaded properly")
            return [], "error.csv"

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Detect faces
        boxes = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, boxes)

        if len(encodings) == 0:
            print("No face detected")
            return [], "no_face.csv"

        present_students = []

        for encoding in encodings:
            matches = face_recognition.compare_faces(known_encodings, encoding)
            name = "Unknown"

            face_distances = face_recognition.face_distance(known_encodings, encoding)
            best_match_index = np.argmin(face_distances)

            if matches[best_match_index]:
                name = known_names[best_match_index]

            if name != "Unknown":
                present_students.append(name)

        present_students = list(set(present_students))

        # Generate CSV
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_name = f"attendance_{timestamp}.csv"
        file_path = os.path.join("attendance", file_name)

        df = pd.DataFrame({
            "Name": present_students,
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Time": datetime.now().strftime("%H:%M:%S")
        })

        df.to_csv(file_path, index=False)

        return present_students, file_name

    except Exception as e:
        print("ERROR in mark_attendance:", str(e))
        return [], "error.csv"