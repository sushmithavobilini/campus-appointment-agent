import os
import sqlite3
import hashlib
import hmac
from datetime import datetime, date, time, timedelta
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = Path(os.getenv("CAMPUS_DB_PATH", str(APP_DIR / "campus_demo.db")))

st.set_page_config(
    page_title="Campus Appointment Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEPARTMENTS = [
    "Faculty Members",
    "Academic Advisors",
    "Placement Office",
    "Accommodation Department",
    "Transportation Department",
    "IT Department",
    "Student Affairs",
    "Cultural Department",
    "Administration",
]

def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex() + ":" + digest.hex()

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), 200_000
        ).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False

def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student','staff')),
            full_name TEXT NOT NULL,
            srn TEXT,
            gender TEXT,
            course TEXT,
            study_year TEXT,
            department TEXT,
            designation TEXT,
            room_no TEXT,
            block_name TEXT
        );
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            staff_id INTEGER NOT NULL,
            department TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            staff_notes TEXT DEFAULT '',
            queries_addressed TEXT DEFAULT '',
            resolution_status TEXT DEFAULT 'Not recorded',
            follow_up TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES users(id),
            FOREIGN KEY(staff_id) REFERENCES users(id),
            UNIQUE(staff_id, appointment_date, appointment_time)
        );
        """)

        # Fictional demo accounts only. Replace before any real institutional use.
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            demo_users = [
                ("student.demo", hash_password("StudentDemo123!"), "student",
                 "Aarav Demo", "DEMO-STU-001", "Prefer not to say",
                 "BBA Business Analytics", "Year 3", None, None, None, None),
                ("staff.placement", hash_password("StaffDemo123!"), "staff",
                 "Dr. Placement Demo", None, None, None, None,
                 "Placement Office", "Placement Officer", "B-204", "Block B"),
                ("staff.advisor", hash_password("StaffDemo123!"), "staff",
                 "Ms. Advisor Demo", None, None, None, None,
                 "Academic Advisors", "Academic Advisor", "A-108", "Block A"),
                ("staff.it", hash_password("StaffDemo123!"), "staff",
                 "Mr. IT Demo", None, None, None, None,
                 "IT Department", "IT Support Officer", "IT-012", "IT Block"),
            ]
            conn.executemany("""
                INSERT INTO users
                (username,password_hash,role,full_name,srn,gender,course,study_year,
                 department,designation,room_no,block_name)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, demo_users)

def query_all(sql, params=()):
    with connect() as conn:
        return conn.execute(sql, params).fetchall()

def execute(sql, params=()):
    with connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid

def get_user(username):
    rows = query_all("SELECT * FROM users WHERE username = ?", (username,))
    return rows[0] if rows else None

def login():
    st.title("Campus Appointment Agent")
    st.caption("A student-services appointment prototype")
    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Your campus, easier to navigate.")
        st.write(
            "Find the right department, book an appointment, and keep track of "
            "follow-up actions through one simple portal."
        )
        st.info(
            "Prototype notice: use fictional demo accounts only. This is not an "
            "official PES University system."
        )
        st.markdown("**Departments supported in the prototype**")
        st.write(" · ".join(DEPARTMENTS))
    with right:
        st.subheader("Sign in")
        role = st.radio("I am signing in as", ["Student", "Staff"], horizontal=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Sign in", type="primary", use_container_width=True):
            user = get_user(username.strip())
            expected_role = role.lower()
            if user and user["role"] == expected_role and verify_password(password, user["password_hash"]):
                st.session_state.user_id = user["id"]
                st.session_state.username = user["username"]
                st.session_state.last_activity = datetime.now().timestamp()
                st.rerun()
            else:
                st.error("Login failed. Check the demo credentials and selected role.")
        with st.expander("Demo accounts"):
            st.markdown(
                "- **Student:** `student.demo` / `StudentDemo123!`\n"
                "- **Staff:** `staff.placement` / `StaffDemo123!`\n"
                "- **Staff:** `staff.advisor` / `StaffDemo123!`\n"
                "- **Staff:** `staff.it` / `StaffDemo123!`"
            )
            st.caption("These accounts are fictional and intended only for this prototype.")

def current_user():
    rows = query_all("SELECT * FROM users WHERE id = ?", (st.session_state.user_id,))
    return rows[0] if rows else None

def profile_panel(user):
    st.subheader("Profile")
    st.write(f"**Name:** {user['full_name']}")
    st.write(f"**Account type:** {user['role'].title()}")
    if user["role"] == "student":
        st.write(f"**SRN:** {user['srn'] or 'Not set'}")
        st.write(f"**Gender:** {user['gender'] or 'Not set'}")
        st.write(f"**Course:** {user['course'] or 'Not set'}")
        st.write(f"**Year of study:** {user['study_year'] or 'Not set'}")
    else:
        st.write(f"**Department:** {user['department'] or 'Not set'}")
        st.write(f"**Designation:** {user['designation'] or 'Not set'}")
        st.write(f"**Room:** {user['room_no'] or 'Not set'}")
        st.write(f"**Block:** {user['block_name'] or 'Not set'}")
    with st.expander("Edit profile"):
        if user["role"] == "student":
            name = st.text_input("Full name", user["full_name"])
            gender = st.text_input("Gender", user["gender"] or "")
            course = st.text_input("Course", user["course"] or "")
            year = st.text_input("Year of study", user["study_year"] or "")
            if st.button("Save profile"):
                execute("UPDATE users SET full_name=?, gender=?, course=?, study_year=? WHERE id=?",
                        (name, gender, course, year, user["id"]))
                st.success("Profile updated.")
                st.rerun()
        else:
            name = st.text_input("Full name", user["full_name"])
            room = st.text_input("Room number", user["room_no"] or "")
            block = st.text_input("Block", user["block_name"] or "")
            if st.button("Save staff profile"):
                execute("UPDATE users SET full_name=?, room_no=?, block_name=? WHERE id=?",
                        (name, room, block, user["id"]))
                st.success("Profile updated.")
                st.rerun()
    with st.expander("Change password"):
        current = st.text_input("Current password", type="password", key="current_pw")
        new = st.text_input("New password (minimum 10 characters)", type="password", key="new_pw")
        confirm = st.text_input("Confirm new password", type="password", key="confirm_pw")
        if st.button("Update password"):
            fresh = get_user(user["username"])
            if not verify_password(current, fresh["password_hash"]):
                st.error("Current password is incorrect.")
            elif len(new) < 10:
                st.error("Use at least 10 characters.")
            elif new != confirm:
                st.error("The passwords do not match.")
            else:
                execute("UPDATE users SET password_hash=? WHERE id=?",
                        (hash_password(new), user["id"]))
                st.success("Password changed. Sign out and sign in with the new password.")

def student_dashboard(user):
    st.title(f"Welcome, {user['full_name'].split()[0]} 👋")
    st.caption("Student dashboard")
    upcoming = query_all("""
        SELECT a.*, s.full_name AS staff_name, s.room_no, s.block_name
        FROM appointments a JOIN users s ON s.id=a.staff_id
        WHERE a.student_id=? AND a.status NOT IN ('Cancelled','Rejected')
        ORDER BY a.appointment_date, a.appointment_time
    """, (user["id"],))
    c1, c2, c3 = st.columns(3)
    c1.metric("Appointments", len(upcoming))
    c2.metric("Departments", len(DEPARTMENTS))
    c3.metric("Account", "Student")
    book_tab, appt_tab, ai_tab = st.tabs(["Book appointment", "My appointments", "AI assistant"])
    with book_tab:
        st.subheader("Book an appointment")
        dept = st.selectbox("Department", DEPARTMENTS)
        staff = query_all("SELECT * FROM users WHERE role='staff' AND department=?", (dept,))
        if not staff:
            st.info("No demo staff have been added to this department yet. The full build will include staff management for all departments.")
        else:
            staff_map = {f"{x['full_name']} — {x['designation']}": x for x in staff}
            staff_label = st.selectbox("Staff member", list(staff_map.keys()))
            chosen = staff_map[staff_label]
            st.caption(f"Office: {chosen['room_no'] or 'TBC'}, {chosen['block_name'] or 'TBC'}")
            appt_date = st.date_input("Date", min_value=date.today(), value=date.today() + timedelta(days=1))
            appt_time = st.selectbox("Time", ["10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30"])
            reason = st.text_area("Reason for appointment", placeholder="Briefly explain what you need help with")
            if st.button("Request appointment", type="primary"):
                if not reason.strip():
                    st.error("Please enter a reason for the appointment.")
                else:
                    try:
                        execute("""
                            INSERT INTO appointments
                            (student_id,staff_id,department,appointment_date,appointment_time,
                             reason,status,created_at)
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (user["id"], chosen["id"], dept, appt_date.isoformat(),
                              appt_time, reason.strip(), "Pending", datetime.now().isoformat()))
                        st.success("Appointment request saved. Check My appointments for its status.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("That staff member already has an appointment at this time. Choose another slot.")
    with appt_tab:
        if not upcoming:
            st.info("You don't have any appointments yet.")
        for a in upcoming:
            with st.container(border=True):
                st.markdown(f"**{a['department']} — {a['staff_name']}**")
                st.write(f"{a['appointment_date']} at {a['appointment_time']} · {a['status']}")
                st.write(f"Office: {a['room_no'] or 'TBC'}, {a['block_name'] or 'TBC'}")
                st.write(f"Reason: {a['reason']}")
                if a["status"] in ("Pending", "Confirmed") and st.button("Cancel appointment", key=f"cancel_{a['id']}"):
                    execute("UPDATE appointments SET status='Cancelled' WHERE id=? AND student_id=?",
                            (a["id"], user["id"]))
                    st.rerun()
    with ai_tab:
        st.subheader("🤖 Campus AI Assistant")
        st.write("Type naturally. Gemini integration will be added in the next milestone.")
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        prompt = st.chat_input("e.g. need to meet placement sir tmrw aftnoon")
        if prompt:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            response = (
                "I can help you with that. In this first milestone, please use the "
                "Book appointment tab to submit a request. In the next milestone, "
                "Gemini will interpret short forms, identify the department and help "
                "you complete the booking conversationally."
            )
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.write(response)

def staff_dashboard(user):
    st.title(f"Welcome, {user['full_name'].split()[0]} 👋")
    st.caption(f"{user['department']} · Staff dashboard")
    rows = query_all("""
        SELECT a.*, u.full_name AS student_name, u.srn, u.course, u.study_year
        FROM appointments a JOIN users u ON u.id=a.student_id
        WHERE a.staff_id=?
        ORDER BY a.appointment_date, a.appointment_time
    """, (user["id"],))
    pending = sum(1 for r in rows if r["status"] == "Pending")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total requests", len(rows))
    c2.metric("Pending", pending)
    c3.metric("Office", user["room_no"] or "TBC")
    st.subheader("Your appointments")
    if not rows:
        st.info("No appointments have been requested yet.")
    for a in rows:
        with st.container(border=True):
            st.markdown(f"**{a['student_name']}** · {a['srn'] or 'No SRN'}")
            st.write(f"{a['appointment_date']} at {a['appointment_time']} · {a['status']}")
            st.write(f"{a['course'] or ''} · {a['study_year'] or ''}")
            st.write(f"Reason: {a['reason']}")
            if a["status"] == "Pending":
                x, y = st.columns(2)
                if x.button("Confirm", key=f"confirm_{a['id']}"):
                    execute("UPDATE appointments SET status='Confirmed' WHERE id=? AND staff_id=?",
                            (a["id"], user["id"]))
                    st.rerun()
                if y.button("Reject", key=f"reject_{a['id']}"):
                    execute("UPDATE appointments SET status='Rejected' WHERE id=? AND staff_id=?",
                            (a["id"], user["id"]))
                    st.rerun()
            if a["status"] in ("Confirmed", "Completed"):
                with st.expander("Post-meeting record"):
                    notes = st.text_area("Reason / meeting context", value=a["staff_notes"] or a["reason"], key=f"notes_{a['id']}")
                    queries = st.text_area("Queries addressed", value=a["queries_addressed"] or "", key=f"queries_{a['id']}")
                    resolution = st.selectbox(
                        "Resolution status",
                        ["Not recorded", "Resolved", "Pending", "Referred to another department"],
                        index=["Not recorded", "Resolved", "Pending", "Referred to another department"].index(a["resolution_status"] or "Not recorded"),
                        key=f"resolution_{a['id']}"
                    )
                    follow_up = st.text_area("Follow-up action", value=a["follow_up"] or "", key=f"followup_{a['id']}")
                    if st.button("Save meeting record", key=f"save_notes_{a['id']}"):
                        execute("""
                            UPDATE appointments SET staff_notes=?, queries_addressed=?,
                            resolution_status=?, follow_up=?, status='Completed'
                            WHERE id=? AND staff_id=?
                        """, (notes, queries, resolution, follow_up, a["id"], user["id"]))
                        st.success("Meeting record saved.")
                        st.rerun()

def main():
    init_db()
    if "user_id" not in st.session_state:
        login()
        return
    user = current_user()
    if not user:
        st.session_state.clear()
        st.rerun()
        return

    # This is a basic prototype inactivity check. Production-grade idle expiry needs
    # a verified browser-activity heartbeat and server-side session enforcement.
    now = datetime.now().timestamp()
    last = st.session_state.get("last_activity", now)
    if now - last > 300:
        st.session_state.clear()
        st.warning("You were signed out after five minutes of inactivity. Please sign in again.")
        st.rerun()
        return
    st.session_state.last_activity = now

    with st.sidebar:
        st.markdown("## 🏫 Campus Agent")
        st.caption("Prototype portal")
        st.write(f"Signed in as **{user['full_name']}**")
        page = st.radio("Navigation", ["Dashboard", "Profile", "About"])
        st.divider()
        if st.button("Sign out", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    if page == "Profile":
        profile_panel(user)
    elif page == "About":
        st.title("About Campus Appointment Agent")
        st.write("A prototype for helping students find departments, book staff appointments and track follow-up actions.")
        st.warning("Not an official university service. Use fictional demo data only.")
        st.write("Contact: xxxx@gmail.com")
        st.write("Project contacts: Sushmitha Vobilini · 987xxxxx | Samshitha Srikanth · 765xxxxx")
    elif user["role"] == "student":
        student_dashboard(user)
    else:
        staff_dashboard(user)

if __name__ == "__main__":
    main()
