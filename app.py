import os, hashlib, hmac, json
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
import streamlit as st

try:
    from google import genai
except ImportError:
    genai = None

st.set_page_config(page_title="Campus Appointment Agent", page_icon="🤖", layout="wide")
DATABASE_URL = os.getenv("DATABASE_URL", "")
DEPARTMENTS = ["Placement Office", "Academic Advisors", "IT Department"]
CAMPUS_TZ = ZoneInfo("Asia/Kolkata")
SLOTS = ["10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30"]

def hash_pw(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex() + ":" + digest.hex()

def verify_pw(password, stored):
    try:
        salt, digest = stored.split(":", 1)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
        return hmac.compare_digest(candidate, digest)
    except Exception:
        return False


def db():
    """Open a short-lived PostgreSQL connection using the private DATABASE_URL secret."""
    url = ""
    try:
        url = st.secrets.get("DATABASE_URL", "")
    except Exception:
        url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL is missing from Streamlit Secrets.")
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=5)

@st.cache_resource
def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS users(
      id BIGSERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
      role TEXT NOT NULL, full_name TEXT NOT NULL, srn TEXT, gender TEXT, course TEXT, study_year TEXT,
      department TEXT, designation TEXT, room_no TEXT, block_name TEXT,
      is_active BOOLEAN NOT NULL DEFAULT TRUE
    );
    CREATE TABLE IF NOT EXISTS appointments(
      id BIGSERIAL PRIMARY KEY,
      student_id BIGINT NOT NULL REFERENCES users(id),
      staff_id BIGINT NOT NULL REFERENCES users(id),
      department TEXT NOT NULL, appointment_date TEXT NOT NULL, appointment_time TEXT NOT NULL,
      reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending',
      staff_notes TEXT NOT NULL DEFAULT '', queries_addressed TEXT NOT NULL DEFAULT '',
      resolution_status TEXT NOT NULL DEFAULT 'Not recorded', follow_up TEXT NOT NULL DEFAULT '',
      created_at TEXT,
      CONSTRAINT unique_staff_slot UNIQUE(staff_id, appointment_date, appointment_time)
    );
    """
    with db() as conn:
        with conn.cursor() as cur:
            for statement in schema.split(";"):
                if statement.strip():
                    cur.execute(statement)
            # Safe schema migration for existing PostgreSQL deployments.
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")
            # Migrate the previous prototype's seeded demo accounts without deleting appointment history.
            cur.execute("""UPDATE users SET is_active=FALSE, username=CONCAT('disabled_student_', id),
                           password_hash=%s, full_name='Deleted Student', srn=NULL, gender=NULL,
                           course=NULL, study_year=NULL
                           WHERE role='student' AND username='student.demo' AND is_active=TRUE""",
                        (hash_pw(os.urandom(32).hex()),))
            staff_migrations = [
                ("Dr. Ananya Rao", "Dr. Placement Demo", "staff.placement", "Placement Office"),
                ("Ms. Kavya Nair", "Ms. Advisor Demo", "staff.advisor", "Academic Advisors"),
                ("Mr. Rahul Mehta", "Mr. IT Demo", "staff.it", "IT Department"),
            ]
            for real_name, old_name, old_username, dept in staff_migrations:
                cur.execute("""UPDATE users SET full_name=%s, username=%s
                               WHERE role='staff' AND department=%s
                               AND (full_name=%s OR username=%s)
                               AND NOT EXISTS (SELECT 1 FROM users existing WHERE existing.username=%s AND existing.id<>users.id)""",
                            (real_name, real_name, dept, old_name, old_username, real_name))
            cur.execute("SELECT COUNT(*) AS n FROM users")
            count = cur.fetchone()["n"]
            if count == 0:
                users = [
                  ("Dr. Ananya Rao",hash_pw("ChangeMe123!"),"staff","Dr. Ananya Rao",None,None,None,None,"Placement Office","Placement Officer","B-204","Block B"),
                  ("Ms. Kavya Nair",hash_pw("ChangeMe123!"),"staff","Ms. Kavya Nair",None,None,None,None,"Academic Advisors","Academic Advisor","A-108","Block A"),
                  ("Mr. Rahul Mehta",hash_pw("ChangeMe123!"),"staff","Mr. Rahul Mehta",None,None,None,None,"IT Department","IT Support Officer","IT-012","IT Block"),
                ]
                cur.executemany("""INSERT INTO users
                  (username,password_hash,role,full_name,srn,gender,course,study_year,department,designation,room_no,block_name)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", users)

def all_rows(sql, args=()):
    # Keep existing application queries while translating SQLite placeholders to PostgreSQL.
    sql = sql.replace("?", "%s")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()

def run(sql, args=()):
    sql = sql.replace("?", "%s")
    is_insert = sql.lstrip().upper().startswith("INSERT")
    if is_insert and "RETURNING" not in sql.upper():
        sql = sql.rstrip().rstrip(";") + " RETURNING id"
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            if is_insert:
                row = cur.fetchone()
                return row["id"] if row else None
            return cur.rowcount

def user_by_name(username):
    rows = all_rows("SELECT * FROM users WHERE username=?", (username,))
    return rows[0] if rows else None

def get_user():
    rows = all_rows("SELECT * FROM users WHERE id=?", (st.session_state.uid,))
    return rows[0] if rows else None

def login_page():
    st.title("🏫 Campus Appointment Agent")
    st.caption("A student-services appointment prototype")
    a, b = st.columns([1.1, 1])
    with a:
        st.subheader("Your campus, easier to navigate.")
        st.write("Find the right department, book appointments and track follow-up actions in one place.")
        st.info("Prototype only. Not an official university system. Use fictional demo accounts.")
        st.write("Departments: " + " · ".join(DEPARTMENTS))
    with b:
        sign_in_tab, register_tab = st.tabs(["Sign in", "Register student account"])
        with sign_in_tab:
            st.subheader("Sign in")
            role = st.radio("Login as", ["Student", "Staff"], horizontal=True)
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Sign in", type="primary", use_container_width=True):
                u = user_by_name(username.strip())
                if u and u.get("is_active", True) and u["role"] == role.lower() and verify_pw(password, u["password_hash"]):
                    st.session_state.uid = u["id"]
                    st.session_state.last_activity = datetime.now().timestamp()
                    st.rerun()
                else:
                    st.error("Login failed. Check your username, password and account status.")
            st.caption("Student login uses your SRN. Staff sign in using their full name as the username.")
        with register_tab:
            st.subheader("Create a student account")
            st.caption("Staff accounts are created by an authorised administrator; public staff registration is disabled.")
            with st.form("student_registration_form"):
                reg_name = st.text_input("Full name")
                reg_srn = st.text_input("SRN")
                reg_gender = st.selectbox("Gender", ["Prefer not to say", "Female", "Male", "Other"])
                reg_course = st.text_input("Course", placeholder="e.g. BBA Business Analytics")
                reg_year = st.selectbox("Year of study", ["Year 1", "Year 2", "Year 3", "Year 4"])
                reg_password = st.text_input("Create password (6+ characters, at least one letter and one number)", type="password")
                reg_confirm = st.text_input("Confirm password", type="password")
                reg_submit = st.form_submit_button("Create account", type="primary", use_container_width=True)
            if reg_submit:
                if not all([reg_name.strip(), reg_srn.strip(), reg_course.strip(), reg_password]):
                    st.error("Please fill in all required fields.")
                elif len(reg_password) < 6 or not any(ch.isalpha() for ch in reg_password) or not any(ch.isdigit() for ch in reg_password):
                    st.error("Use at least 6 characters, including at least one letter and one number.")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                elif user_by_name(reg_srn.strip()):
                    st.error("That SRN is already being used as a login. Check it or contact the administrator.")
                elif all_rows("SELECT id FROM users WHERE srn=? AND role='student' AND is_active=TRUE", (reg_srn.strip(),)):
                    st.error("An active student account already uses that SRN.")
                else:
                    try:
                        run("""INSERT INTO users
                            (username,password_hash,role,full_name,srn,gender,course,study_year,is_active)
                            VALUES(?,?,?,?,?,?,?,?,TRUE)""",
                            (reg_srn.strip(), hash_pw(reg_password), "student", reg_name.strip(),
                             reg_srn.strip(), reg_gender, reg_course.strip(), reg_year))
                        st.success("Account created. Sign in using your SRN and password.")
                    except psycopg.errors.UniqueViolation:
                        st.error("That username is already registered. Please choose another.")

def profile_page(u):
    st.header("Profile")
    if u["role"] == "student":
        st.write(f"**Name:** {u['full_name']}  \n**SRN:** {u['srn']}  \n**Gender:** {u['gender']}  \n**Course:** {u['course']}  \n**Year:** {u['study_year']}")
        with st.form("edit_student"):
            name = st.text_input("Full name", u["full_name"])
            gender = st.text_input("Gender", u["gender"] or "")
            course = st.text_input("Course", u["course"] or "")
            year = st.text_input("Year of study", u["study_year"] or "")
            if st.form_submit_button("Save profile"):
                run("UPDATE users SET full_name=?,gender=?,course=?,study_year=? WHERE id=?", (name,gender,course,year,u["id"]))
                st.success("Profile updated."); st.rerun()
    else:
        st.write(f"**Name:** {u['full_name']}  \n**Department:** {u['department']}  \n**Designation:** {u['designation']}  \n**Room:** {u['room_no']}  \n**Block:** {u['block_name']}")
        with st.form("edit_staff"):
            name = st.text_input("Full name", u["full_name"])
            room = st.text_input("Room number", u["room_no"] or "")
            block = st.text_input("Block", u["block_name"] or "")
            if st.form_submit_button("Save profile"):
                run("UPDATE users SET full_name=?,room_no=?,block_name=? WHERE id=?", (name,room,block,u["id"]))
                st.success("Profile updated."); st.rerun()
    with st.expander("Change password"):
        current = st.text_input("Current password", type="password")
        new = st.text_input("New password (6+ characters, at least one letter and one number)", type="password")
        confirm = st.text_input("Confirm new password", type="password")
        if st.button("Change password"):
            fresh = user_by_name(u["username"])
            if not verify_pw(current, fresh["password_hash"]): st.error("Current password is incorrect.")
            elif len(new) < 10: st.error("Password must be at least 10 characters.")
            elif new != confirm: st.error("Passwords do not match.")
            else:
                run("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(new),u["id"]))
                st.success("Password updated.")

    st.divider()
    with st.expander("Delete account", expanded=False):
        st.warning("Deleting your account disables sign-in and removes identifying profile details. Appointment history is retained in anonymised form to preserve staff-side records.")
        st.caption("Enter your current password and type DELETE to confirm.")
        delete_password = st.text_input("Current password", type="password", key="delete_account_password")
        delete_confirm = st.text_input("Type DELETE to confirm", key="delete_account_confirm")
        if st.button("Delete my account", type="primary", key="delete_my_account"):
            fresh = user_by_name(u["username"])
            if u["role"] != "student":
                st.error("Staff accounts cannot self-delete in this prototype. Ask an authorised administrator.")
            elif not fresh or not verify_pw(delete_password, fresh["password_hash"]):
                st.error("Current password is incorrect.")
            elif delete_confirm.strip() != "DELETE":
                st.error("Type DELETE exactly to confirm.")
            else:
                run("""UPDATE appointments
                       SET reason='Account deleted', staff_notes='', queries_addressed='',
                           follow_up='', resolution_status='Not recorded'
                       WHERE student_id=?""", (u["id"],))
                run("""UPDATE users SET is_active=FALSE, username=?, password_hash=?,
                       full_name='Deleted Student', srn=NULL, gender=NULL, course=NULL,
                       study_year=NULL WHERE id=?""",
                    (f"deleted_student_{u['id']}", hash_pw(os.urandom(32).hex()), u["id"]))
                st.session_state.clear()
                st.success("Your account has been deleted. You have been signed out.")
                st.rerun()

def free_slots(staff_id, day):
    """Return slots that are not booked and have not already started (campus local time)."""
    busy = {r["appointment_time"] for r in all_rows("""SELECT appointment_time FROM appointments
      WHERE staff_id=? AND appointment_date=? AND status NOT IN ('Cancelled','Rejected')""", (staff_id,day))}
    available = [slot for slot in SLOTS if slot not in busy]
    try:
        selected_day = date.fromisoformat(str(day))
    except (TypeError, ValueError):
        return []
    campus_now = datetime.now(CAMPUS_TZ)
    today = campus_now.date()
    if selected_day < today:
        return []
    if selected_day == today:
        current_time = campus_now.strftime("%H:%M")
        # A slot is no longer bookable once its start time has passed.
        available = [slot for slot in available if slot > current_time]
    return available

@st.cache_resource(show_spinner=False)
def gemini_client(api_key):
    if genai is None:
        raise RuntimeError("Gemini SDK is not installed. Check requirements.txt.")
    return genai.Client(api_key=api_key)

def gemini_parse(message):
    if genai is None:
        raise RuntimeError("Gemini SDK is not installed. Check requirements.txt.")
    try:
        key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing from Streamlit Secrets.")
    client = gemini_client(key)
    prompt = f"""Today: {datetime.now(CAMPUS_TZ).date().isoformat()}. Interpret a student request for a campus appointment.
Departments: {DEPARTMENTS}. Understand short forms like tmrw=tomorrow, appt=appointment, cncl=cancel, resched=reschedule.
Return JSON only with keys intent (book/view/cancel/reschedule/find_department/other), department, date (new date for reschedule), time (new time), time_preference (morning/afternoon/evening), target_date (existing appointment date), target_time (existing appointment time), reason, staff_name_hint, clarifying_question, summary. Use ISO date YYYY-MM-DD and 24-hour HH:MM. Never claim an action has completed. Leave unclear fields empty.
Student message: {message}"""
    # One fast model call; only fall back immediately if the primary model is unavailable.
    last_error = None
    for model_name in ("gemini-3.1-flash-lite", "gemini-3.8-flash"):
        try:
            response = client.models.generate_content(
                model=model_name, contents=prompt,
                config={"response_mime_type": "application/json", "temperature": 0.1},
            )
            result = json.loads(response.text or "{}")
            if not isinstance(result, dict):
                raise ValueError("Unexpected AI response")
            return result
        except Exception as exc:
            last_error = exc
            # Don't sleep/retry on Streamlit's request thread; try the fallback once.
    raise RuntimeError("The AI service is busy. Please try again shortly.") from last_error


def stage_appointment_change(u, intent, action):
    """Stage a cancellation/reschedule; never mutate an appointment before explicit confirmation."""
    target_date = (intent.get("target_date") or "").strip()
    target_time = (intent.get("target_time") or "").strip()
    rows = all_rows("""SELECT a.*, s.full_name AS staff_name FROM appointments a
        JOIN users s ON s.id=a.staff_id
        WHERE a.student_id=? AND a.status IN ('Pending','Confirmed') AND a.appointment_date>=?
        ORDER BY a.appointment_date,a.appointment_time""", (u["id"], date.today().isoformat()))
    if target_date:
        rows = [r for r in rows if r["appointment_date"] == target_date]
    if target_time:
        rows = [r for r in rows if r["appointment_time"] == target_time]
    if not target_date and len(rows) > 1:
        return None, "You have multiple upcoming appointments. Please include the existing appointment date (and time if needed) so I change the right one."
    if not rows:
        return None, "I couldn't identify a matching upcoming appointment. Please include its existing date and time. No changes were made."
    appt = rows[0]
    pending = {"action": action, "appointment_id": appt["id"], "department": appt["department"],
               "staff_name": appt["staff_name"], "old_day": appt["appointment_date"],
               "old_slot": appt["appointment_time"]}
    if action == "reschedule":
        new_day_text = (intent.get("date") or "").strip()
        new_time = (intent.get("time") or "").strip()
        preference = (intent.get("time_preference") or "").lower()
        try:
            new_day = date.fromisoformat(new_day_text)
        except ValueError:
            new_day = None
        if not new_day or new_day < date.today():
            return None, "What future date would you like to move it to? No changes were made."
        if new_time and new_time not in SLOTS:
            return None, "That time isn't in the demo schedule. Choose one of the available demo slots. No changes were made."
        available = free_slots(appt["staff_id"], new_day.isoformat())
        # The appointment's current slot is considered busy, so only remove it from the busy list when staying on its current date.
        if new_day.isoformat() == appt["appointment_date"]:
            available.append(appt["appointment_time"])
        available = sorted(set(available))
        if new_time:
            available = [slot for slot in available if slot == new_time]
        elif "morning" in preference:
            available = [slot for slot in available if slot < "12:00"]
        elif "afternoon" in preference:
            available = [slot for slot in available if "12:00" <= slot < "17:00"]
        elif "evening" in preference:
            available = [slot for slot in available if slot >= "17:00"]
        available = [slot for slot in available if not (new_day.isoformat() == appt["appointment_date"] and slot == appt["appointment_time"])]
        if not available:
            return None, "I couldn't find a free slot for that new date/time. Try another slot. No changes were made."
        pending["new_day"] = new_day.isoformat()
        pending["new_slot"] = available[0]
    return pending, "Review the change below. Nothing will be changed until you confirm."

def render_change_confirmation(state_key, u, button_prefix):
    pending = st.session_state.get(state_key)
    if not pending:
        return
    with st.container(border=True):
        st.markdown("**Confirm appointment change**")
        st.write(f"**Action:** {'Cancel' if pending['action'] == 'cancel' else 'Reschedule'}")
        st.write(f"**Appointment:** {pending['department']} — {pending['staff_name']}")
        st.write(f"**Current slot:** {pending['old_day']} at {pending['old_slot']}")
        if pending['action'] == 'reschedule':
            st.write(f"**New slot:** {pending['new_day']} at {pending['new_slot']}")
        yes, no = st.columns(2)
        if yes.button("Confirm change", key=f"{button_prefix}_change_yes", type="primary"):
            try:
                if pending["action"] == "cancel":
                    run("UPDATE appointments SET status='Cancelled' WHERE id=? AND student_id=? AND status IN ('Pending','Confirmed')", (pending["appointment_id"], u["id"]))
                    result_message = "Your appointment has been cancelled."
                else:
                    run("UPDATE appointments SET appointment_date=?,appointment_time=? WHERE id=? AND student_id=? AND status IN ('Pending','Confirmed')",
                        (pending["new_day"], pending["new_slot"], pending["appointment_id"], u["id"]))
                    result_message = "Your appointment has been rescheduled."
                # Share the result with both chat interfaces so it remains visible after switching tabs.
                st.session_state.setdefault("chat", []).append({"role":"assistant", "content":result_message})
                st.session_state.setdefault("floating_ai_messages", []).append({"role":"assistant", "content":result_message})
                st.session_state.pop(state_key, None)
                st.rerun()
            except psycopg.errors.UniqueViolation:
                st.error("That slot was just taken. No change was made; please choose another time.")
        if no.button("Keep appointment unchanged", key=f"{button_prefix}_change_no"):
            st.session_state.pop(state_key, None)
            st.rerun()

def floating_ai_widget(u):
    """Floating student-facing AI chat panel; booking requests always require confirmation."""
    st.markdown("""
    <style>
    div.st-key-floating_ai_toggle {
        position: fixed; right: 22px; bottom: 18px; z-index: 100001;
        width: 66px; background: transparent;
    }
    div.st-key-floating_ai_toggle button {
        width: 58px; height: 58px; border-radius: 50%;
        box-shadow: 0 4px 18px rgba(0,0,0,.25);
        font-size: 25px; padding: 0;
    }
    div.st-key-floating_ai_panel {
        position: fixed; right: 22px; bottom: 88px; z-index: 100000;
        width: min(390px, calc(100vw - 36px)); max-height: 70vh;
        overflow-y: auto; padding: 14px; border: 1px solid rgba(128,128,128,.45);
        border-radius: 16px; background: var(--secondary-background-color);
        box-shadow: 0 8px 28px rgba(0,0,0,.24);
    }
    </style>
    """, unsafe_allow_html=True)

    if "floating_ai_open" not in st.session_state:
        st.session_state.floating_ai_open = False
    if "floating_ai_messages" not in st.session_state:
        st.session_state.floating_ai_messages = [
            {"role": "assistant", "content": "Hi! I can help you request a campus appointment. Try: “I need placement guidance tomorrow afternoon.”"}
        ]
    if "floating_ai_pending" not in st.session_state:
        st.session_state.floating_ai_pending = None

    with st.container(key="floating_ai_toggle"):
        if st.button("🤖", key="floating_ai_toggle_button", help="Open Campus AI Assistant"):
            st.session_state.floating_ai_open = not st.session_state.floating_ai_open
            st.rerun()

    if not st.session_state.floating_ai_open:
        return

    with st.container(key="floating_ai_panel", border=True):
        top1, top2 = st.columns([4, 1])
        top1.markdown("### 🤖 Campus Assistant")
        if top2.button("✕", key="floating_ai_close", help="Close chat"):
            st.session_state.floating_ai_open = False
            st.rerun()

        for msg in st.session_state.floating_ai_messages[-8:]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        pending = st.session_state.floating_ai_pending
        if pending:
            st.markdown("**Review appointment request**")
            st.write(f"**Department:** {pending['department']}")
            st.write(f"**Staff:** {pending['staff_name']}")
            st.write(f"**Date/time:** {pending['day']} at {pending['slot']}")
            st.write(f"**Reason:** {pending['reason']}")
            yes, no = st.columns(2)
            if yes.button("Confirm", key="floating_ai_confirm", type="primary", use_container_width=True):
                try:
                    run("""INSERT INTO appointments(student_id,staff_id,department,appointment_date,appointment_time,reason,status,created_at)
                        VALUES(?,?,?,?,?,?,?,?)""", (u["id"], pending["staff_id"], pending["department"],
                        pending["day"], pending["slot"], pending["reason"], "Pending", datetime.now().isoformat()))
                    st.session_state.floating_ai_messages.append({"role":"assistant","content":"Your appointment request was saved as Pending. Staff still needs to confirm it."})
                    st.session_state.floating_ai_pending = None
                    st.rerun()
                except psycopg.errors.UniqueViolation:
                    st.error("That slot was just taken. No booking was made. Please try another time.")
            if no.button("Don't book", key="floating_ai_decline", use_container_width=True):
                st.session_state.floating_ai_pending = None
                st.session_state.floating_ai_messages.append({"role":"assistant","content":"No booking was made."})
                st.rerun()

        render_change_confirmation("ai_pending_change", u, "floating_ai")

        with st.form("floating_ai_message_form", clear_on_submit=True):
            message = st.text_input("Message", placeholder="Ask to book an appointment…", label_visibility="collapsed")
            sent = st.form_submit_button("Send", use_container_width=True)
        if sent and message.strip():
            st.session_state.floating_ai_messages.append({"role":"user","content":message.strip()})
            try:
                intent = gemini_parse(message.strip())
                kind = (intent.get("intent") or "other").lower()
                answer = intent.get("summary") or "I understood your request."
                if kind == "book":
                    dept = intent.get("department") or ""
                    day_text = intent.get("date") or ""
                    tm = intent.get("time") or ""
                    pref = (intent.get("time_preference") or "").lower()
                    reason = (intent.get("reason") or "").strip() or message.strip()
                    hint = (intent.get("staff_name_hint") or "").lower()
                    if dept not in DEPARTMENTS:
                        answer = "Which department do you need? For example, Placement Office, IT Department or Academic Advisors."
                    elif not day_text:
                        answer = intent.get("clarifying_question") or "What date would you like to meet?"
                    else:
                        try:
                            day = date.fromisoformat(day_text)
                        except ValueError:
                            day = None
                        if not day or day < date.today():
                            answer = "Please give me a valid future date. No booking was made."
                        else:
                            staff_list = all_rows("SELECT * FROM users WHERE role='staff' AND department=? ORDER BY full_name", (dept,))
                            if hint:
                                matched = [staff for staff in staff_list if hint in staff["full_name"].lower() or hint in (staff["designation"] or "").lower()]
                                if matched:
                                    staff_list = matched
                            options = []
                            for staff in staff_list:
                                available = free_slots(staff["id"], day.isoformat())
                                if tm:
                                    available = [slot for slot in available if slot == tm]
                                elif "morning" in pref:
                                    available = [slot for slot in available if slot < "12:00"]
                                elif "afternoon" in pref:
                                    available = [slot for slot in available if "12:00" <= slot < "17:00"]
                                elif "evening" in pref:
                                    available = [slot for slot in available if slot >= "17:00"]
                                for slot in available:
                                    options.append((staff, slot))
                            if not options:
                                answer = "I couldn't find a free demo slot matching that request. Try another date or time. No booking was made."
                            else:
                                staff, slot = options[0]
                                st.session_state.floating_ai_pending = {
                                    "staff_id": staff["id"], "staff_name": staff["full_name"],
                                    "department": dept, "day": day.isoformat(), "slot": slot, "reason": reason
                                }
                                answer = "I found a possible slot. Review the details below and confirm if you want to submit the request."
                elif kind == "view":
                    answer = "Your appointments are shown in the My appointments section of your dashboard."
                elif kind in ("cancel", "reschedule"):
                    pending_change, answer = stage_appointment_change(u, intent, kind)
                    if pending_change:
                        st.session_state.ai_pending_change = pending_change
                elif kind == "find_department":
                    answer = intent.get("clarifying_question") or "Tell me briefly what issue you need help with."
                else:
                    answer = intent.get("clarifying_question") or "I can help with appointment requests and finding the right campus department. What do you need?"
                st.session_state.floating_ai_messages.append({"role":"assistant","content":answer})
            except Exception:
                st.session_state.floating_ai_messages.append({"role":"assistant","content":"Sorry, I couldn't process that request. Please try again in a moment, or use Book appointment."})
            st.rerun()

@st.fragment(run_every="30s")
def student_page(u):
    st.title(f"Welcome, {u['full_name'].split()[0]} 👋")
    st.caption("Student dashboard")
    booking_tab, appointments_tab = st.tabs(["Book appointment", "My appointments"])
    with booking_tab:
        department = st.selectbox("Department", DEPARTMENTS)
        staff = all_rows("SELECT * FROM users WHERE role='staff' AND department=? ORDER BY full_name", (department,))
        if not staff:
            st.info("No demo staff have been added to this department yet.")
        else:
            staff_map = {f"{s['full_name']} — {s['designation']}":s for s in staff}
            label = st.selectbox("Staff member", list(staff_map))
            s = staff_map[label]
            st.caption(f"Office: {s['room_no'] or 'TBC'}, {s['block_name'] or 'TBC'}")
            day = st.date_input("Date", min_value=datetime.now(CAMPUS_TZ).date(), value=datetime.now(CAMPUS_TZ).date()+timedelta(days=1))
            available_slots = free_slots(s["id"], day.isoformat())
            if not available_slots:
                st.warning("No available time slots for this staff member on the selected date. Choose another date or staff member.")
                slot = None
            else:
                slot = st.selectbox("Available time slots", available_slots)
            reason = st.text_area("Reason for appointment")
            if st.button("Request appointment", type="primary", disabled=not available_slots):
                if not reason.strip(): st.error("Please enter a reason.")
                elif not slot: st.error("Please choose an available time slot.")
                else:
                    try:
                        run("""INSERT INTO appointments(student_id,staff_id,department,appointment_date,appointment_time,reason,status,created_at)
                          VALUES(?,?,?,?,?,?,?,?)""", (u["id"],s["id"],department,day.isoformat(),slot,reason.strip(),"Pending",datetime.now().isoformat()))
                        st.success("Appointment request saved as Pending."); st.rerun()
                    except psycopg.errors.UniqueViolation: st.error("That slot was just booked. Choose another available time.")
    with appointments_tab:
        appts = all_rows("""SELECT a.*,s.full_name staff_name,s.room_no,s.block_name FROM appointments a
          JOIN users s ON s.id=a.staff_id WHERE a.student_id=? ORDER BY a.appointment_date,a.appointment_time""", (u["id"],))
        if not appts: st.info("No appointments yet.")
        for a in appts:
            with st.container(border=True):
                st.markdown(f"**{a['department']} — {a['staff_name']}**")
                st.write(f"{a['appointment_date']} at {a['appointment_time']} · {a['status']}")
                st.write(f"Office: {a['room_no']}, {a['block_name']}  \nReason: {a['reason']}")
                if a["status"] in ("Pending","Confirmed") and st.button("Cancel appointment", key=f"cancel_{a['id']}"):
                    run("UPDATE appointments SET status='Cancelled' WHERE id=? AND student_id=?", (a["id"],u["id"]))
                    st.rerun()
                if a["resolution_status"] != "Not recorded":
                    st.write(f"**Outcome:** {a['resolution_status']}")
                    if a["follow_up"]: st.write(f"**Follow-up:** {a['follow_up']}")

def staff_page(u):
    st.title(f"Welcome, {u['full_name'].split()[0]} 👋")
    st.caption(f"{u['department']} · Staff dashboard")
    rows = all_rows("""SELECT a.*,u.full_name student_name,u.srn,u.course,u.study_year FROM appointments a
      JOIN users u ON u.id=a.student_id WHERE a.staff_id=? ORDER BY a.appointment_date,a.appointment_time""", (u["id"],))
    if not rows: st.info("No appointments have been requested yet.")
    for a in rows:
        with st.container(border=True):
            st.markdown(f"**{a['student_name']}** · {a['srn'] or 'No SRN'}")
            st.write(f"{a['appointment_date']} at {a['appointment_time']} · {a['status']}")
            st.write(f"{a['course'] or ''} · {a['study_year'] or ''}")
            st.write(f"Reason: {a['reason']}")
            if a["status"] == "Pending":
                c1,c2 = st.columns(2)
                if c1.button("Confirm",key=f"confirm_{a['id']}"):
                    run("UPDATE appointments SET status='Confirmed' WHERE id=? AND staff_id=?", (a["id"],u["id"])); st.rerun()
                if c2.button("Reject",key=f"reject_{a['id']}"):
                    run("UPDATE appointments SET status='Rejected' WHERE id=? AND staff_id=?", (a["id"],u["id"])); st.rerun()
            if a["status"] in ("Confirmed","Completed"):
                with st.expander("Post-meeting record"):
                    notes = st.text_area("Meeting reason/context",value=a["staff_notes"] or a["reason"],key=f"notes_{a['id']}")
                    queries = st.text_area("Queries addressed",value=a["queries_addressed"] or "",key=f"queries_{a['id']}")
                    resolution = st.selectbox("Resolution",["Not recorded","Resolved","Pending","Referred to another department"],
                        index=["Not recorded","Resolved","Pending","Referred to another department"].index(a["resolution_status"] or "Not recorded"),key=f"resolution_{a['id']}")
                    follow = st.text_area("Follow-up action",value=a["follow_up"] or "",key=f"follow_{a['id']}")
                    if st.button("Save meeting record",key=f"save_{a['id']}"):
                        run("""UPDATE appointments SET staff_notes=?,queries_addressed=?,resolution_status=?,follow_up=?,status='Completed'
                          WHERE id=? AND staff_id=?""",(notes,queries,resolution,follow,a["id"],u["id"]))
                        st.success("Meeting record saved."); st.rerun()



def main():
    init_db()
    if "uid" not in st.session_state:
        login_page(); return
    u = get_user()
    if not u:
        st.session_state.clear(); st.rerun(); return
    # Prototype-only inactivity check; production deployment needs server-side session expiry.
    now = datetime.now().timestamp()
    if now - st.session_state.get("last_activity",now) > 300:
        st.session_state.clear(); st.warning("Signed out after inactivity. Please log in again."); st.rerun(); return
    st.session_state.last_activity = now
    with st.sidebar:
        st.markdown("## 🏫 Campus Agent")
        page = st.radio("Navigation",["Dashboard","Profile","About"])
        st.divider()
        if st.button("Sign out",use_container_width=True):
            st.session_state.clear(); st.rerun()
    if page == "Profile": profile_page(u)
    elif page == "About":
        st.title("About Campus Appointment Agent")
        st.write("A prototype for campus appointment booking and student-support follow-up.")
        st.warning("Not an official university system. Use fictional data only.")
        st.write("Contact: xxxx@gmail.com")
        st.write("Sushmitha Vobilini · 987xxxxx")
        st.write("Samshitha Srikanth · 765xxxxx")
    elif u["role"] == "student":
        student_page(u)
        floating_ai_widget(u)
    else: staff_page(u)

if __name__ == "__main__":
    main()
