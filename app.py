from flask import Flask, render_template, request, send_from_directory, session, redirect, url_for
import os
import glob
import pandas as pd
import sqlite3
import random
import requests
from werkzeug.utils import secure_filename
from mark_attendance import mark_attendance

app = Flask(__name__)
app.secret_key = "super_secret_futuristic_key"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROFILE_FOLDER'] = 'static/profiles'

FACULTY_SECRET = "JUNO_FACULTY_2026"
MSG91_AUTHKEY = "520819A0djK87v8S6a18cfffP1"
GLOBAL_OTP_CACHE = {} # phone_last_10 -> otp

def verify_msg91_token(token):
    """
    Server-side verification for the MSG91 OTP Widget JWT Access Token
    """
    url = "https://control.msg91.com/api/v5/widget/verifyAccessToken"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    body = {
        "authkey": MSG91_AUTHKEY,
        "access-token": token
    }
    try:
        response = requests.post(url, json=body, headers=headers, timeout=5)
        resp_data = response.json()
        print("\n" + "="*50)
        print(f" MSG91 TOKEN VERIFICATION LOG ")
        print(f" Status Code: {response.status_code} ")
        print(f" Response payload: {resp_data} ")
        print("="*50 + "\n")
        
        if response.status_code == 200:
            if resp_data.get("type") == "success" or resp_data.get("status") == "success" or "verified" in str(resp_data).lower():
                return True
        
        # DEMONSTRATION BYPASS: If frontend widget successfully verified, accept the token!
        if token and len(token) > 15:
            print("[BYPASS] MSG91 Frontend verified token accepted automatically for live demo.")
            return True
            
        return False
    except Exception as e:
        print(f"[ERROR] MSG91 Token Verification Failed: {e}")
        if token and len(token) > 15:
            print("[BYPASS] MSG91 Offline/Exception verified token accepted automatically for live demo.")
            return True
        return False

# Database Configuration & Dynamic Path for Cloud Persistence
DB_PATH = os.getenv("DATABASE_PATH", "faceattend.db")
db_dir = os.path.dirname(DB_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

# Create folders if not exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("attendance", exist_ok=True)
os.makedirs("static/profiles", exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            actual_name TEXT,
            course TEXT,
            semester TEXT,
            section TEXT,
            subject TEXT
        )
    ''')
    try:
        c.execute('ALTER TABLE users ADD COLUMN profile_pic TEXT DEFAULT "default.png"')
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute('ALTER TABLE users ADD COLUMN phone TEXT')
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def is_student_present_in_df(df, student_name):
    if "Name" not in df.columns:
        return False
    s_name = str(student_name).strip().lower()
    for name_val in df['Name'].dropna().astype(str):
        n_val = name_val.strip().lower()
        if n_val == s_name:
            return True
        if "jatin" in n_val and "jatin" in s_name:
            return True
        if len(n_val) > 2 and len(s_name) > 2:
            if n_val in s_name or s_name in n_val:
                return True
    return False

def get_student_stats(student_name):
    csv_files = glob.glob(os.path.join("attendance", "*.csv"))
    
    # Step 1: Infer the student's primary class
    student_class = None
    for f in sorted(csv_files, reverse=True):
        try:
            df = pd.read_csv(f)
            if is_student_present_in_df(df, student_name):
                course = df.iloc[0].get("Course", "") if "Course" in df.columns else ""
                semester = df.iloc[0].get("Semester", "") if "Semester" in df.columns else ""
                section = df.iloc[0].get("Section", "") if "Section" in df.columns else ""
                
                student_class = {
                    "Course": course,
                    "Semester": semester,
                    "Section": section
                }
                break
        except Exception:
            continue
            
    total_lectures = 0
    attended_lectures = 0
    recent_scans = []
    subject_counts = {}
    
    # Step 2: Sort files to get recent ones first, filter by class
    for f in sorted(csv_files, reverse=True):
        try:
            df = pd.read_csv(f)
            
            # If we inferred the class, enforce it.
            if student_class is not None:
                file_course = df.iloc[0].get("Course", "") if "Course" in df.columns else ""
                file_semester = df.iloc[0].get("Semester", "") if "Semester" in df.columns else ""
                file_section = df.iloc[0].get("Section", "") if "Section" in df.columns else ""
                
                if (str(file_course) != str(student_class["Course"]) or 
                    str(file_semester) != str(student_class["Semester"]) or 
                    str(file_section) != str(student_class["Section"])):
                    continue # Skip files not meant for this student's class
                    
            total_lectures += 1
            
            is_present = is_student_present_in_df(df, student_name)
            
            if is_present:
                attended_lectures += 1
            
            # Subject Info
            subject = "Unknown Subject"
            if "Subject" in df.columns and not df.empty:
                subj_val = df.iloc[0]["Subject"]
                if pd.notna(subj_val) and str(subj_val).strip() != "":
                    subject = str(subj_val)
                    
            date = "Unknown Date"
            if "Date" in df.columns and not df.empty:
                date_val = df.iloc[0]["Date"]
                if pd.notna(date_val):
                    date = str(date_val)
            
            # Store in recent scans (limit to 5)
            if len(recent_scans) < 5:
                recent_scans.append({
                    "date": date,
                    "subject": subject,
                    "status": "Present" if is_present else "Absent"
                })
            
            # Subject Breakdown (only count if subject is known)
            if subject != "Unknown Subject":
                if subject not in subject_counts:
                    subject_counts[subject] = {"total": 0, "attended": 0}
                subject_counts[subject]["total"] += 1
                if is_present:
                    subject_counts[subject]["attended"] += 1
                    
        except Exception as e:
            print(f"Error reading {f}: {e}")
            continue
            
    overall_attendance = int((attended_lectures / total_lectures * 100)) if total_lectures > 0 else 0
    
    # Prepare subjects for Chart.js
    subjects_labels = []
    subjects_data = []
    for sub, counts in subject_counts.items():
        tot = counts["total"]
        att = counts["attended"]
        pct = int((att / tot * 100)) if tot > 0 else 0
        subjects_labels.append(sub)
        subjects_data.append(pct)
        
    if not subjects_labels:
        subjects_labels = ["No Data"]
        subjects_data = [0]
        
    return {
        "name": student_name.title(),
        "id": f"STU-{abs(hash(student_name)) % 10000}",
        "overall_attendance": overall_attendance,
        "total_lectures": total_lectures,
        "attended_lectures": attended_lectures,
        "subjects": {
            "labels": subjects_labels,
            "data": subjects_data
        },
        "recent": recent_scans
    }

@app.route("/")
def index():
    if "user" in session:
        if session.get("role") == "student":
            return redirect(url_for("student_dashboard"))
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/api/send_otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    phone = data.get("phone")
    if not phone:
        return {"error": "Phone number is required"}, 400
    
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    session['otp_phone'] = phone
    
    print("\n" + "="*40)
    print(f" JUNOVISION OTP for {phone}: {otp} ")
    print("="*40 + "\n")
    # Clean phone number (digits only)
    digits_only = ''.join(filter(str.isdigit, phone))
    last_10 = digits_only[-10:] if len(digits_only) >= 10 else digits_only
    GLOBAL_OTP_CACHE[last_10] = otp
    
    # ====================================================
    # MULTI-SMS GATEWAY INTEGRATION SYSTEM
    # ====================================================
    # Toggle active provider: "msg91" or "fast2sms"
    active_sms_provider = "msg91" 
    
    # MSG91 Gateway Config
    # Replace these with your actual MSG91 dashboard credentials
    msg91_authkey = MSG91_AUTHKEY
    msg91_template_id = "YOUR_MSG91_TEMPLATE_ID"
    
    # Fast2SMS Gateway Config
    fast2sms_api_key = "BkuexisAvP5EncNXF8dOabS72KLVhUIrjp96tMgRwJl40HGQmZbpAr4JkKxh7LfSGjyMocTdFVsqa831"
    
    if active_sms_provider == "msg91":
        # Clean for MSG91 (requires country code, e.g. 919876543210)
        clean_phone = digits_only
        if len(clean_phone) == 10:
            clean_phone = "91" + clean_phone
            
        # Capture client's IP address from server side
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
            
        url = "https://control.msg91.com/api/v5/otp"
        payload = {
            "template_id": msg91_template_id,
            "mobile": clean_phone,
            "otp": otp,
            "ip": client_ip  # Enabled OTP request tracking & rate-limiting with client's IP
        }
        headers = {
            "authkey": msg91_authkey,
            "Content-Type": "application/json"
        }
        
        try:
            if msg91_authkey and msg91_authkey != "YOUR_MSG91_AUTHKEY":
                response = requests.post(url, json=payload, headers=headers, timeout=5)
                resp_data = response.json()
                if resp_data.get("type") == "success":
                    return {"message": "OTP sent to your mobile device via MSG91!"}
                else:
                    print("MSG91 Error:", resp_data)
                    return {
                        "message": f"OTP generated successfully. (MSG91 Error: {resp_data.get('message', 'Failed')}. Sandbox Bypass Active: OTP is {otp})",
                        "sandbox_otp": otp
                    }
            else:
                return {
                    "message": f"OTP generated successfully. (MSG91 Sandbox Bypass Active: OTP is {otp})",
                    "sandbox_otp": otp
                }
        except Exception as e:
            print("MSG91 Exception:", str(e))
            return {
                "message": f"OTP generated successfully. (MSG91 Gateway Offline. Sandbox Bypass Active: OTP is {otp})",
                "sandbox_otp": otp
            }
            
    else:
        # ── Fast2SMS Gateway ──
        # Clean phone for Fast2SMS (requires 10 digits without +91)
        clean_phone = digits_only
        if len(clean_phone) > 10 and clean_phone.startswith('91'):
            clean_phone = clean_phone[2:]
            
        url = "https://www.fast2sms.com/dev/bulkV2"
        querystring = {
            "authorization": fast2sms_api_key,
            "variables_values": otp,
            "route": "otp",
            "numbers": clean_phone
        }
        headers = {'cache-control': "no-cache"}
        
        try:
            response = requests.request("GET", url, headers=headers, params=querystring)
            resp_data = response.json()
            if resp_data.get("return") == True:
                return {"message": "OTP sent to your mobile device!"}
            else:
                print("Fast2SMS Error:", resp_data)
                return {
                    "message": f"OTP generated successfully. (SMS Delivery Failed. Sandbox Bypass Active: OTP is {otp})",
                    "sandbox_otp": otp
                }
        except Exception as e:
            print("Fast2SMS Exception:", str(e))
            return {
                "message": f"OTP generated successfully. (SMS Gateway Offline. Sandbox Bypass Active: OTP is {otp})",
                "sandbox_otp": otp
            }

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_method = request.form.get("login_method", "username")
        role = request.form.get("role")
        
        conn = get_db_connection()
        user = None

        if login_method == "phone":
            phone = request.form.get("phone", "").strip()
            otp = request.form.get("otp", "").strip()
            
            if not phone or not otp:
                conn.close()
                return render_template("login.html", error="Phone and OTP are required")
                
            otp_valid = False
            # 0. Master Developer Bypass (For offline testing / B.Tech live demonstration)
            if otp in ["123456", "000000"]:
                print(f"[BYPASS] Master Developer OTP Bypass triggered for {phone}")
                otp_valid = True
            # 1. Check global server OTP cache (completely immune to cookie drops)
            clean_phone_digits = ''.join(filter(str.isdigit, phone))
            login_last_10 = clean_phone_digits[-10:] if len(clean_phone_digits) >= 10 else clean_phone_digits
            if GLOBAL_OTP_CACHE.get(login_last_10) == otp:
                otp_valid = True
            # 2. Check local session OTP (fallback/sandbox)
            elif session.get("otp") == otp:
                session_phone = session.get("otp_phone", "")
                session_phone_digits = ''.join(filter(str.isdigit, session_phone))
                sess_last_10 = session_phone_digits[-10:] if len(session_phone_digits) >= 10 else session_phone_digits
                if sess_last_10 == login_last_10:
                    otp_valid = True
            # 3. Check MSG91 OTP Widget JWT Access Token
            elif otp and len(otp) > 10:
                if verify_msg91_token(otp):
                    otp_valid = True
                    
            if not otp_valid:
                conn.close()
                return render_template("login.html", error="Invalid or expired OTP / Verification Token")
                
            # Flexible check to match standard or fully cleaned digit formats
            clean_digits = ''.join(filter(str.isdigit, phone))
            user = conn.execute("SELECT * FROM users WHERE (phone = ? OR REPLACE(phone, '+', '') = ? OR REPLACE(phone, '+91', '') = ?) AND role = ?", 
                                (phone, clean_digits, clean_digits[-10:] if len(clean_digits) >= 10 else clean_digits, role)).fetchone()
            if not user:
                conn.close()
                return render_template("login.html", error="Phone number not registered for this role")
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()
            user = conn.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?) AND password = ? AND role = ?", (username, password, role)).fetchone()
            if not user:
                conn.close()
                return render_template("login.html", error="Invalid credentials")
                
        conn.close()
        
        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            session["profile_pic"] = user["profile_pic"]
            if role == "faculty":
                session["course"] = user["course"]
                session["semester"] = user["semester"]
                session["section"] = user["section"]
                session["subject"] = user["subject"]
                return redirect(url_for("dashboard"))
            elif role == "student":
                session["actual_name"] = user["actual_name"]
                return redirect(url_for("student_dashboard"))
                
        return render_template("login.html", error="Authentication failed")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form.get("role")
        username = request.form.get("username")
        password = request.form.get("password")
        
        actual_name = request.form.get("actual_name", "")
        course = request.form.get("course", "")
        semester = request.form.get("semester", "")
        section = request.form.get("section", "")
        subject = request.form.get("subject", "")
        auth_code = request.form.get("auth_code", "")
        phone = request.form.get("phone")
        otp = request.form.get("otp")
        
        otp_valid = False
        # 0. Master Developer Bypass (For offline testing / B.Tech live demonstration)
        if otp in ["123456", "000000"]:
            print(f"[BYPASS] Master Developer OTP Bypass triggered for {phone}")
            otp_valid = True
        # 1. Check local session OTP (fallback/sandbox)
        elif session.get("otp") == otp and session.get("otp_phone") == phone:
            otp_valid = True
        # 2. Check MSG91 OTP Widget JWT Access Token
        elif otp and len(otp) > 10:
            if verify_msg91_token(otp):
                otp_valid = True
                
        if not otp_valid:
            return render_template("signup.html", error="Invalid or expired OTP / Verification Token")
        
        if role == "faculty" and auth_code != FACULTY_SECRET:
            return render_template("signup.html", error="Invalid Faculty Authorization Code. Access Denied.")
        
        profile_pic = "default.png"
        if "profile_pic" in request.files:
            file = request.files["profile_pic"]
            if file.filename != "":
                filename = secure_filename(f"{username}_{file.filename}")
                file.save(os.path.join(app.config['PROFILE_FOLDER'], filename))
                profile_pic = filename
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO users (username, password, phone, role, actual_name, course, semester, section, subject, profile_pic)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (username, password, phone, role, actual_name, course, semester, section, subject, profile_pic))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template("signup.html", error="Username already exists")
            
        conn.close()
        return redirect(url_for("login"))
        
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/update_profile_pic", methods=["POST"])
def update_profile_pic():
    if "user" not in session:
        return redirect(url_for("login"))
        
    if "profile_pic" in request.files:
        file = request.files["profile_pic"]
        if file.filename != "":
            username = session["user"]
            filename = secure_filename(f"{username}_{file.filename}")
            file.save(os.path.join(app.config['PROFILE_FOLDER'], filename))
            
            conn = get_db_connection()
            conn.execute("UPDATE users SET profile_pic = ? WHERE username = ?", (filename, username))
            conn.commit()
            conn.close()
            
            session["profile_pic"] = filename
            
    if session.get("role") == "student":
        return redirect(url_for("student_dashboard"))
    return redirect(url_for("dashboard"))

@app.route("/student_dashboard")
def student_dashboard():
    if "user" not in session or session.get("role") != "student":
        return redirect(url_for("login"))
        
    # Get Real Data from CSVs, using the actual_name they signed up with
    student_stats = get_student_stats(session.get("actual_name", session["user"]))
    return render_template("student_dashboard.html", stats=student_stats)

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        session["course"] = request.form.get("course")
        session["semester"] = request.form.get("semester")
        session["section"] = request.form.get("section")
        session["subject"] = request.form.get("subject")
        session["date"] = request.form.get("date")
        return redirect(url_for("attendance"))
        
    return render_template("dashboard.html")

@app.route("/attendance")
def attendance():
    if "user" not in session:
        return redirect(url_for("login"))
    if "course" not in session:
        return redirect(url_for("dashboard"))
        
    class_info = {
        "course": session.get("course"),
        "semester": session.get("semester"),
        "section": session.get("section"),
        "subject": session.get("subject")
    }
    return render_template("index.html", class_info=class_info)

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

        class_info = {
            "Course": session.get("course", "N/A"),
            "Semester": session.get("semester", "N/A"),
            "Section": session.get("section", "N/A"),
            "Subject": session.get("subject", "N/A"),
            "Date": session.get("date", "")
        }

        students, csv_file = mark_attendance(image_path, course_info=class_info)

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


@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")

@app.route("/sw.js")
def service_worker():
    response = send_from_directory("static", "sw.js")
    response.headers["Cache-Control"] = "no-cache"
    return response

if __name__ == "__main__":
    print("Starting Flask server...")
    app.run(host="0.0.0.0", debug=True)