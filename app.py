import os, sqlite3, hashlib, hmac, json
from datetime import datetime, date, timedelta
from pathlib import Path
import streamlit as st

try:
    from google import genai
except ImportError:
    genai = None

st.set_page_config(page_title="Campus Appointment Agent", page_icon="🤖", layout="wide")
DB_PATH = Path(os.getenv("CAMPUS_DB_PATH", str(Path(__file__).parent / "campus_demo.db")))
DEPARTMENTS = ["Faculty Members", "Academic Advisors", "Placement Office", "Accommodation Department",
               "Transportation Department", "IT Department", "Student Affairs", "Cultural Department", "Administration"]
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
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT, role TEXT, full_name TEXT,
          srn TEXT, gender TEXT, course TEXT, study_year TEXT, department TEXT, designation TEXT,
          room_no TEXT, block_name TEXT);
        CREATE TABLE IF NOT EXISTS appointments(
          id INTEGER PRIMARY KEY, student_id INTEGER, staff_id INTEGER, department TEXT,
          appointment_date TEXT, appointment_time TEXT, reason TEXT, status TEXT DEFAULT 'Pending',
          staff_notes TEXT DEFAULT '', queries_addressed TEXT DEFAULT '',
          resolution_status TEXT DEFAULT 'Not recorded', follow_up TEXT DEFAULT '', created_at TEXT,
          UNIQUE(staff_id, appointment_date, appointment_time));
        """)
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            users = [
              ("student.demo",hash_pw("StudentDemo123!"),"student","Aarav Demo","DEMO-STU-001","Prefer not to say","BBA Business Analytics","Year 3",None,None,None,None),
              ("staff.placement",hash_pw("StaffDemo123!"),"staff","Dr. Placement Demo",None,None,None,None,"Placement Office","Placement Officer","B-204","Block B"),
              ("staff.advisor",hash_pw("StaffDemo123!"),"staff","Ms. Advisor Demo",None,None,None,None,"Academic Advisors","Academic Advisor","A-108","Block A"),
              ("staff.it",hash_pw("StaffDemo123!"),"staff","Mr. IT Demo",None,None,None,None,"IT Department","IT Support Officer","IT-012","IT Block"),
            ]
            c.executemany("""INSERT INTO users(username,password_hash,role,full_name,srn,gender,course,study_year,department,designation,room_no,block_name)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", users)

def all_rows(sql, args=()):
    with db() as c:
        return c.execute(sql, args).fetchall()

def run(sql, args=()):
    with db() as c:
        cur = c.execute(sql, args); c.commit(); return cur.lastrowid

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
        st.subheader("Sign in")
        role = st.radio("Login as", ["Student", "Staff"], horizontal=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Sign in", type="primary", use_container_width=True):
            u = user_by_name(username.strip())
            if u and u["role"] == role.lower() and verify_pw(password, u["password_hash"]):
                st.session_state.uid = u["id"]
                st.session_state.last_activity = datetime.now().timestamp()
                st.rerun()
            else:
                st.error("Login failed. Check username, password and role.")
        with st.expander("Fictional demo accounts"):
            st.code("Student: student.demo / StudentDemo123!\nPlacement staff: staff.placement / StaffDemo123!\nAdvisor: staff.advisor / StaffDemo123!\nIT staff: staff.it / StaffDemo123!")

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
        new = st.text_input("New password (10+ characters)", type="password")
        confirm = st.text_input("Confirm new password", type="password")
        if st.button("Change password"):
            fresh = user_by_name(u["username"])
            if not verify_pw(current, fresh["password_hash"]): st.error("Current password is incorrect.")
            elif len(new) < 10: st.error("Password must be at least 10 characters.")
            elif new != confirm: st.error("Passwords do not match.")
            else:
                run("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(new),u["id"]))
                st.success("Password updated.")

def free_slots(staff_id, day):
    busy = {r["appointment_time"] for r in all_rows("""SELECT appointment_time FROM appointments
      WHERE staff_id=? AND appointment_date=? AND status NOT IN ('Cancelled','Rejected')""", (staff_id,day))}
    return [s for s in SLOTS if s not in busy]

def gemini_parse(message):
    if genai is None: raise RuntimeError("Gemini SDK not installed. Redeploy after updating requirements.txt.")
    try: key = st.secrets["GEMINI_API_KEY"]
    except Exception: key = os.getenv("GEMINI_API_KEY", "")
    if not key: raise RuntimeError("GEMINI_API_KEY is missing from Streamlit Secrets.")
    client = genai.Client(api_key=key)
    prompt = f"""Today is {date.today().isoformat()}. Interpret this student message for a university appointment app.
Understand informal short forms/typos such as tmrw=tomorrow, aftnoon=afternoon, appt=appointment,
cncl=cancel, resched=reschedule, fac=faculty, hod=head of department, pls=please.
Allowed departments: {DEPARTMENTS}.
Return only JSON with keys intent (book/view/cancel/reschedule/find_department/other), department (exact allowed name or empty),
date (YYYY-MM-DD or empty), time (HH:MM 24-hour or empty), time_preference (morning/afternoon/evening/empty),
reason, staff_name_hint, clarifying_question, summary. Resolve relative dates from today. Do not invent availability or claim a booking was made.
If a detail is unclear, leave it empty and ask a concise question.
Student message: {message}"""
    response = client.models.generate_content(model="gemini-3.8-flash", contents=prompt,
        config={"response_mime_type":"application/json", "temperature":0.1})
    result = json.loads(response.text)
    if not isinstance(result, dict): raise ValueError("Unexpected AI response")
    return result

def student_page(u):
    st.title(f"Welcome, {u['full_name'].split()[0]} 👋")
    st.caption("Student dashboard")
    booking_tab, appointments_tab, ai_tab = st.tabs(["Book appointment", "My appointments", "🤖 AI assistant"])
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
            day = st.date_input("Date", min_value=date.today(), value=date.today()+timedelta(days=1))
            slot = st.selectbox("Time", SLOTS)
            reason = st.text_area("Reason for appointment")
            if st.button("Request appointment", type="primary"):
                if not reason.strip(): st.error("Please enter a reason.")
                else:
                    try:
                        run("""INSERT INTO appointments(student_id,staff_id,department,appointment_date,appointment_time,reason,status,created_at)
                          VALUES(?,?,?,?,?,?,?,?)""", (u["id"],s["id"],department,day.isoformat(),slot,reason.strip(),"Pending",datetime.now().isoformat()))
                        st.success("Appointment request saved as Pending."); st.rerun()
                    except sqlite3.IntegrityError: st.error("That slot is already booked. Choose another.")
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
    with ai_tab:
        st.subheader("🤖 Campus AI Assistant")
        st.caption("Try: “need to meet placement sir tmrw aftnoon”")
        if st.session_state.get("ai_debug_error"):
            with st.expander("Gemini diagnostic (for troubleshooting)", expanded=True):
                st.code(st.session_state["ai_debug_error"])
                if st.button("Clear diagnostic", key="clear_ai_diagnostic"):
                    st.session_state.pop("ai_debug_error", None)
                    st.rerun()
        if "chat" not in st.session_state: st.session_state.chat = []
        for m in st.session_state.chat:
            with st.chat_message(m["role"]): st.write(m["content"])
        pending = st.session_state.get("ai_pending")
        if pending:
            with st.container(border=True):
                st.markdown("**Review before submitting**")
                st.write(f"Department: {pending['department']}")
                st.write(f"Staff: {pending['staff_name']}")
                st.write(f"Date: {pending['day']} · Time: {pending['slot']}")
                st.write(f"Reason: {pending['reason']}")
                yes, no = st.columns(2)
                if yes.button("Confirm booking", type="primary"):
                    try:
                        run("""INSERT INTO appointments(student_id,staff_id,department,appointment_date,appointment_time,reason,status,created_at)
                          VALUES(?,?,?,?,?,?,?,?)""", (u["id"],pending["staff_id"],pending["department"],pending["day"],pending["slot"],pending["reason"],"Pending",datetime.now().isoformat()))
                        st.session_state.chat.append({"role":"assistant","content":"Appointment request saved as Pending. The staff member still needs to confirm it."})
                        st.session_state.pop("ai_pending",None); st.rerun()
                    except sqlite3.IntegrityError: st.error("That slot was just taken. No booking was made.")
                if no.button("Don't book"):
                    st.session_state.pop("ai_pending",None); st.rerun()
        message = st.chat_input("Type naturally, short forms are okay...")
        if message:
            st.session_state.chat.append({"role":"user","content":message})
            try:
                intent = gemini_parse(message)
                kind = (intent.get("intent") or "other").lower()
                answer = intent.get("summary") or "I understood your request."
                if kind == "book":
                    dept = intent.get("department") or ""
                    day_text = intent.get("date") or ""
                    tm = intent.get("time") or ""
                    pref = (intent.get("time_preference") or "").lower()
                    reason = (intent.get("reason") or "").strip() or message
                    hint = (intent.get("staff_name_hint") or "").lower()
                    if dept not in DEPARTMENTS:
                        answer = "Which department do you need? For example, Placement Office, IT Department or Academic Advisors."
                    elif not day_text:
                        answer = intent.get("clarifying_question") or "What date would you like to meet?"
                    else:
                        try: day = date.fromisoformat(day_text)
                        except ValueError: day = None
                        if not day or day < date.today():
                            answer = "I couldn't identify a valid future date. Please tell me the date you want."
                        else:
                            staff_list = all_rows("SELECT * FROM users WHERE role='staff' AND department=? ORDER BY full_name", (dept,))
                            if hint:
                                matched = [s for s in staff_list if hint in s["full_name"].lower() or hint in (s["designation"] or "").lower()]
                                if matched: staff_list = matched
                            options = []
                            for s in staff_list:
                                avail = free_slots(s["id"],day.isoformat())
                                if tm: avail = [x for x in avail if x == tm]
                                elif "morning" in pref: avail = [x for x in avail if x < "12:00"]
                                elif "afternoon" in pref: avail = [x for x in avail if "12:00" <= x < "17:00"]
                                elif "evening" in pref: avail = [x for x in avail if x >= "17:00"]
                                for slot in avail: options.append((s,slot))
                            if not options:
                                answer = "I couldn't find a matching free slot in the demo schedule. Try another date or time. No booking was made."
                            else:
                                s, slot = options[0]
                                st.session_state.ai_pending = {"staff_id":s["id"],"staff_name":s["full_name"],"department":dept,
                                    "day":day.isoformat(),"slot":slot,"reason":reason}
                                answer = "I found a possible slot. Review it below and confirm before I submit the request."
                elif kind == "view": answer = "Open My appointments to see your saved bookings and statuses."
                elif kind == "cancel": answer = "Open My appointments and cancel the specific appointment there. No appointment has been cancelled by this message."
                elif kind == "reschedule": answer = "Use My appointments for now. Conversational rescheduling will be added later."
                elif kind == "find_department": answer = intent.get("clarifying_question") or "Tell me briefly what issue you need help with."
                else: answer = intent.get("clarifying_question") or "I can help with booking, viewing appointments, finding a department, cancellation or rescheduling. What do you need?"
                st.session_state.chat.append({"role":"assistant","content":answer})
            except Exception as e:
                # Persist a safe diagnostic across Streamlit's rerun so the error is visible.
                try:
                    secret_key = str(st.secrets.get("GEMINI_API_KEY", ""))
                except Exception:
                    secret_key = os.getenv("GEMINI_API_KEY", "")
                detail = f"{type(e).__name__}: {str(e)[:600]}"
                if secret_key:
                    detail = detail.replace(secret_key, "[REDACTED_API_KEY]")
                st.session_state["ai_debug_error"] = detail
                st.session_state.chat.append({"role":"assistant","content":"Sorry, I couldn't process that request. Please try again or use Book appointment."})
            st.rerun()

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
    elif u["role"] == "student": student_page(u)
    else: staff_page(u)

if __name__ == "__main__":
    main()
