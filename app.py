from flask import Flask, render_template, request, send_from_directory
import os
from mark_attendance import mark_attendance

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Create folders if not exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("attendance", exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "image" not in request.files:
            return {"error": "No image uploaded"}, 400

        file = request.files["image"]

        if file.filename == "":
            return {"error": "Empty filename"}, 400

        image_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(image_path)

        students, csv_file = mark_attendance(image_path)

        return {
            "students": students,
            "csv_file": csv_file
        }

    except Exception as e:
        print("UPLOAD ERROR:", str(e))
        return {"error": str(e)}, 500


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory("attendance", filename, as_attachment=True)


if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(debug=True)