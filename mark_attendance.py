import cv2
import pickle
import pandas as pd
from datetime import datetime
import os

encoding_file = "encodings/encodings.pkl"

def mark_attendance(image_path, course_info=None):
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
            # Stricter tolerance for matching faces from the dataset
            matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.45)
            name = "Unknown"

            face_distances = face_recognition.face_distance(known_encodings, encoding)
            if len(face_distances) > 0:
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

        num_students = max(len(present_students), 1)

        target_date = course_info.get("Date") if course_info and course_info.get("Date") else datetime.now().strftime("%Y-%m-%d")
        # Build CSV Data
        csv_data = {
            "Name": present_students if present_students else [""],
            "Date": [target_date] * num_students,
            "Time": [datetime.now().strftime("%H:%M:%S")] * num_students
        }
        
        if course_info:
            course_val = course_info.get("Course", "")
            sem_val = course_info.get("Semester", "")
            class_val = f"{course_val} - Sem {sem_val}" if course_val else ""

            csv_data["Class"] = [class_val] * num_students
            csv_data["Course"] = [course_val] * num_students
            csv_data["Semester"] = [sem_val] * num_students
            csv_data["Section"] = [course_info.get("Section", "")] * num_students
            csv_data["Subject"] = [course_info.get("Subject", "")] * num_students

        df = pd.DataFrame(csv_data)
        
        if len(present_students) == 0:
            df = df.drop(index=0)

        df.to_csv(file_path, index=False)

        return present_students, file_name

    except Exception as e:
        print("ERROR in mark_attendance:", str(e))
        return [], "error.csv"