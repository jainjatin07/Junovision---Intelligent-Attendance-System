import os
import sqlite3
import glob

def reset_project():
    print("==================================================")
    print("     JUNOVISION SYSTEM PROJECT RESET ENGINE       ")
    print("==================================================")
    
    db_path = 'faceattend.db'
    
    # 1. Clear SQLite Database Tables
    if os.path.exists(db_path):
        try:
            print("\nConnecting to database faceattend.db...")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get table count before clearing
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            msg_count = 0
            try:
                cursor.execute("SELECT COUNT(*) FROM whatsapp_messages")
                msg_count = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                pass
            
            print(f" Wiping {user_count} registered users/logins...")
            cursor.execute("DELETE FROM users")
            
            try:
                cursor.execute("DELETE FROM whatsapp_messages")
            except sqlite3.OperationalError:
                pass
            
            conn.commit()
            
            # Clean database file size (outside of active transaction block)
            conn.execute("VACUUM")
            conn.close()
            
            print("[SUCCESS] Database cleared and compressed successfully!")
        except Exception as e:
            print(f"[WARNING] Error while clearing database: {e}")
    else:
        print("[INFO] Database faceattend.db does not exist yet. It will be initialized on next startup.")

    # 2. Clear old attendance files
    print("\nCleaning old attendance CSV records...")
    attendance_files = glob.glob(os.path.join("attendance", "*.csv"))
    cleared_csv_count = 0
    for file in attendance_files:
        try:
            os.remove(file)
            cleared_csv_count += 1
        except Exception as e:
            print(f"   Could not remove {file}: {e}")
    print(f"[SUCCESS] Removed {cleared_csv_count} old attendance CSV file(s).")

    # 3. Clear custom uploaded profiles
    print("\nCleaning registered profile pictures...")
    profile_pics = glob.glob(os.path.join("static", "profiles", "*"))
    cleared_pic_count = 0
    for pic in profile_pics:
        # Keep default profile avatar if it exists
        if "default.png" in os.path.basename(pic):
            continue
        try:
            os.remove(pic)
            cleared_pic_count += 1
        except Exception as e:
            print(f"   Could not remove {pic}: {e}")
    print(f"[SUCCESS] Removed {cleared_pic_count} uploaded student/faculty profile photo(s).")

    print("\n==================================================")
    print("   RESET COMPLETE: JunoVision is ready for use!   ")
    print("==================================================")

if __name__ == "__main__":
    reset_project()
