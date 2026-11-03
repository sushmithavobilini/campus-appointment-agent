import os, hashlib, hmac, json, base64
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

# Apple-inspired visual layer: royal blue accents, cool light-grey surfaces.
# SaaS-style visual system with theme-aware surfaces and contrast.
_CSS = """<style>
:root { --brand:#315DEB; --brand-strong:#2147C7; --brand-soft:#EAF0FF; --canvas:#F5F7FB; --surface:#FFFFFF; --surface-2:#EEF2F8; --ink:#171D2B; --muted:#5F6B7D; --line:#DCE3EF; --shadow:0 8px 28px rgba(22,39,75,.07); }
html, body, [data-testid="stAppViewContainer"] { background:var(--canvas); color:var(--ink); }
[data-testid="stHeader"] { background:transparent; }
.block-container { max-width:1500px; padding:1.6rem 2.2rem 3rem; }
[data-testid="stSidebar"] { background:var(--surface); border-right:1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding-top:1.4rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 { color:var(--brand-strong); letter-spacing:-.04em; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding:10px 13px; border-radius:12px; margin:3px 0; color:var(--muted); }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:var(--brand-soft); color:var(--brand-strong); }
h1,h2,h3,h4 { color:var(--ink); letter-spacing:-.035em; }
h1 { font-weight:780; } h2,h3 { font-weight:720; }
p, label, [data-testid="stCaptionContainer"], [data-testid="stMarkdownContainer"] { color:var(--muted); }
[data-testid="stVerticalBlockBorderWrapper"] { background:var(--surface); border:1px solid var(--line); border-radius:18px; box-shadow:var(--shadow); }
[data-testid="stMetric"] { background:var(--surface); border:1px solid var(--line); border-radius:16px; padding:16px 18px; }
[data-testid="stMetricLabel"] { color:var(--muted)!important; }
[data-testid="stMetricValue"] { color:var(--brand-strong)!important; font-weight:760; }
.stButton > button, [data-testid="stFormSubmitButton"] button { border-radius:12px; border:1px solid var(--line); background:var(--surface); color:var(--ink); font-weight:650; min-height:42px; transition:all .15s ease; }
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] { background:var(--brand); border-color:var(--brand); color:#fff; }
.stButton > button:hover { border-color:var(--brand); color:var(--brand-strong); transform:translateY(-1px); }
.stButton > button[kind="primary"]:hover { background:var(--brand-strong); color:#fff; }
[data-baseweb="input"] > div, [data-baseweb="select"] > div, [data-baseweb="textarea"] > div { border-radius:11px; background:var(--surface); border-color:var(--line); }
input, textarea { color:var(--ink)!important; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap:7px; background:var(--surface-2); padding:6px; border-radius:14px; border:1px solid var(--line); }
[data-testid="stTabs"] button[role="tab"] { border-radius:10px; padding:9px 15px; color:var(--muted); }
[data-testid="stTabs"] button[aria-selected="true"] { background:var(--surface); color:var(--brand-strong); box-shadow:0 1px 5px rgba(20,40,80,.10); }
[data-testid="stExpander"] { border:1px solid var(--line); border-radius:14px; background:var(--surface); }
[data-testid="stAlert"] { border-radius:13px; }
[data-testid="stNotification"] { border-radius:14px; }
hr { border-color:var(--line); }
.login-hero { min-height:500px; height:100%; padding:36px; border-radius:24px; overflow:hidden; display:flex; flex-direction:column; justify-content:flex-end; color:#fff; background-size:cover; background-position:center; box-shadow:0 16px 40px rgba(13,32,73,.20); position:relative; }
.login-hero:before { content:""; position:absolute; inset:0; background:linear-gradient(180deg,rgba(9,24,54,.08) 5%,rgba(9,24,54,.18) 38%,rgba(8,22,50,.88) 100%); }
.login-hero > * { position:relative; z-index:1; }
.login-eyebrow { color:#DCE7FF; font-size:12px; letter-spacing:.16em; font-weight:800; }
.login-title { color:#fff; font-size:clamp(32px,3.4vw,48px); font-weight:800; line-height:1.05; letter-spacing:-.045em; margin:12px 0; }
.login-copy { color:#E6EDFA; font-size:16px; max-width:500px; line-height:1.6; }
.login-pill { display:inline-block; margin:7px 6px 0 0; padding:8px 12px; border:1px solid rgba(255,255,255,.28); background:rgba(255,255,255,.15); border-radius:999px; color:#fff; font-size:12px; font-weight:650; }
.login-card-title { color:var(--ink); font-size:26px; font-weight:780; letter-spacing:-.04em; }
@media (max-width: 800px) { .block-container { padding:1rem .8rem 2rem; } .login-hero { min-height:300px; padding:24px; } }
/* Streamlit's theme attribute is applied by the active app theme. Override every major surface in dark mode. */
html[data-theme="dark"], body[data-theme="dark"], [data-theme="dark"] { --canvas:#0B1120; --surface:#121B2B; --surface-2:#1A263A; --ink:#F1F5FC; --muted:#B7C2D3; --line:#2A3950; --brand:#7394FF; --brand-strong:#9AB1FF; --brand-soft:#1D2D52; --shadow:0 8px 28px rgba(0,0,0,.22); color-scheme:dark; }
html[data-theme="dark"] body, html[data-theme="dark"] [data-testid="stAppViewContainer"], [data-theme="dark"] [data-testid="stAppViewContainer"] { background:var(--canvas)!important; color:var(--ink)!important; }
html[data-theme="dark"] [data-testid="stHeader"], [data-theme="dark"] [data-testid="stHeader"] { background:rgba(11,17,32,.88)!important; }
html[data-theme="dark"] [data-testid="stSidebar"], [data-theme="dark"] [data-testid="stSidebar"] { background:var(--surface)!important; border-color:var(--line)!important; }
html[data-theme="dark"] h1, html[data-theme="dark"] h2, html[data-theme="dark"] h3, html[data-theme="dark"] h4, html[data-theme="dark"] p, html[data-theme="dark"] label, html[data-theme="dark"] [data-testid="stMarkdownContainer"], [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3, [data-theme="dark"] h4, [data-theme="dark"] p, [data-theme="dark"] label, [data-theme="dark"] [data-testid="stMarkdownContainer"] { color:var(--ink)!important; }
html[data-theme="dark"] [data-testid="stCaptionContainer"], html[data-theme="dark"] [data-testid="stMetricLabel"], [data-theme="dark"] [data-testid="stCaptionContainer"], [data-theme="dark"] [data-testid="stMetricLabel"] { color:var(--muted)!important; }
html[data-theme="dark"] [data-testid="stVerticalBlockBorderWrapper"], html[data-theme="dark"] [data-testid="stMetric"], html[data-theme="dark"] [data-testid="stExpander"], [data-theme="dark"] [data-testid="stVerticalBlockBorderWrapper"], [data-theme="dark"] [data-testid="stMetric"], [data-theme="dark"] [data-testid="stExpander"] { background:var(--surface)!important; border-color:var(--line)!important; }
html[data-theme="dark"] [data-baseweb="input"] > div, html[data-theme="dark"] [data-baseweb="select"] > div, html[data-theme="dark"] [data-baseweb="textarea"] > div, [data-theme="dark"] [data-baseweb="input"] > div, [data-theme="dark"] [data-baseweb="select"] > div, [data-theme="dark"] [data-baseweb="textarea"] > div { background:#172338!important; border-color:var(--line)!important; }
html[data-theme="dark"] input, html[data-theme="dark"] textarea, html[data-theme="dark"] [data-baseweb="select"] *, [data-theme="dark"] input, [data-theme="dark"] textarea, [data-theme="dark"] [data-baseweb="select"] * { color:var(--ink)!important; }
html[data-theme="dark"] [data-testid="stTabs"] [data-baseweb="tab-list"], [data-theme="dark"] [data-testid="stTabs"] [data-baseweb="tab-list"] { background:var(--surface-2)!important; border-color:var(--line)!important; }
html[data-theme="dark"] [data-testid="stTabs"] button[role="tab"], [data-theme="dark"] [data-testid="stTabs"] button[role="tab"] { color:var(--muted)!important; }
html[data-theme="dark"] [data-testid="stTabs"] button[aria-selected="true"], [data-theme="dark"] [data-testid="stTabs"] button[aria-selected="true"] { background:#263858!important; color:#FFFFFF!important; }
html[data-theme="dark"] .stButton > button, html[data-theme="dark"] [data-testid="stFormSubmitButton"] button, [data-theme="dark"] .stButton > button, [data-theme="dark"] [data-testid="stFormSubmitButton"] button { background:#1A2940; border-color:var(--line); color:var(--ink); }
html[data-theme="dark"] .stButton > button[kind="primary"], html[data-theme="dark"] [data-testid="stFormSubmitButton"] button[kind="primary"], [data-theme="dark"] .stButton > button[kind="primary"], [data-theme="dark"] [data-testid="stFormSubmitButton"] button[kind="primary"] { background:#315DEB!important; border-color:#315DEB!important; color:#fff!important; }
html[data-theme="dark"] hr, [data-theme="dark"] hr { border-color:var(--line)!important; }
</style>"""
_bg_path = Path(__file__).with_name("campus_login_bg.png")
_bg64 = base64.b64encode(_bg_path.read_bytes()).decode("ascii") if _bg_path.exists() else ""
_CSS = _CSS.replace("</style>", f'.login-hero {{ background-image:linear-gradient(180deg,rgba(5,18,43,.05),rgba(5,18,43,.76)),url(data:image/png;base64,{_bg64}); }}\n</style>')
st.markdown(_CSS, unsafe_allow_html=True)
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


@st.cache_resource
def connection_pool(database_url):
    """Reuse a small PostgreSQL connection pool instead of reconnecting on every query."""
    from psycopg_pool import ConnectionPool
    return ConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=5,
        timeout=4,
        kwargs={"row_factory": dict_row},
        open=True,
    )

def db():
    """Borrow a pooled PostgreSQL connection for a short transaction."""
    try:
        database_url = st.secrets.get("DATABASE_URL", "")
    except Exception:
        database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from Streamlit Secrets.")
    return connection_pool(database_url).connection()

@st.cache_resource
def init_db():
    schema = """
    CREATE TABLE IF NOT EXISTS users(
      id BIGSERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
      role TEXT NOT NULL, full_name TEXT NOT NULL, srn TEXT, gender TEXT, course TEXT, study_year TEXT,
      department TEXT, designation TEXT, room_no TEXT, block_name TEXT,
      is_active BOOLEAN NOT NULL DEFAULT TRUE, is_chairperson BOOLEAN NOT NULL DEFAULT FALSE
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
      booking_source TEXT NOT NULL DEFAULT 'staff',
      reschedule_status TEXT NOT NULL DEFAULT 'None',
      reschedule_date TEXT,
      reschedule_time TEXT,
      reschedule_reason TEXT NOT NULL DEFAULT '',
      CONSTRAINT unique_staff_slot UNIQUE(staff_id, appointment_date, appointment_time)
    );
    CREATE TABLE IF NOT EXISTS student_concerns(
      id BIGSERIAL PRIMARY KEY,
      student_id BIGINT NOT NULL REFERENCES users(id),
      subject TEXT NOT NULL, message TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'Submitted',
      chairperson_reply TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS notifications(
      id BIGSERIAL PRIMARY KEY,
      user_id BIGINT NOT NULL REFERENCES users(id),
      title TEXT NOT NULL, message TEXT NOT NULL,
      is_read BOOLEAN NOT NULL DEFAULT FALSE,
      created_at TEXT NOT NULL
    );
    """
    with db() as conn:
        with conn.cursor() as cur:
            for statement in schema.split(";"):
                if statement.strip():
                    cur.execute(statement)
            # Safe schema migration for existing PostgreSQL deployments.
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_chairperson BOOLEAN NOT NULL DEFAULT FALSE")
            cur.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS booking_source TEXT NOT NULL DEFAULT 'staff'")
            cur.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reschedule_status TEXT NOT NULL DEFAULT 'None'")
            cur.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reschedule_date TEXT")
            cur.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reschedule_time TEXT")
            cur.execute("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reschedule_reason TEXT NOT NULL DEFAULT ''")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_active_role_name ON users(role,is_active,full_name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_srn_active ON users(srn,is_active)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_appointments_staff_date ON appointments(staff_id,appointment_date,status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_appointments_student_date ON appointments(student_id,appointment_date)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notifications(user_id,created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_concerns_created ON student_concerns(created_at DESC)")
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
            cur.execute("SELECT id FROM users WHERE role='staff' AND is_chairperson=TRUE LIMIT 1")
            if not cur.fetchone():
                cur.execute("""INSERT INTO users
                  (username,password_hash,role,full_name,department,designation,room_no,block_name,is_chairperson)
                  VALUES(%s,%s,'staff',%s,%s,%s,%s,%s,TRUE)
                  ON CONFLICT(username) DO NOTHING""",
                  ("Chairperson",hash_pw("ChangeMe123!"),"Chairperson",
                   "Chairperson Office","Chairperson","Admin Block","Admin Block"))
            cur.execute("UPDATE users SET is_chairperson=TRUE WHERE role='staff' AND username='Chairperson'")

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
    left, right = st.columns([1.12, 0.88], gap="large", vertical_alignment="center")
    with left:
        st.markdown("""<div class="login-hero">
          <div class="login-eyebrow">CAMPUS APPOINTMENT AGENT</div>
          <div class="login-title">Your campus.<br>One connected place.</div>
          <div class="login-copy">Book appointments, connect with the right department and stay updated on every step of your campus support journey.</div>
          <div><span class="login-pill">Placement Office</span><span class="login-pill">Academic Advisors</span><span class="login-pill">IT Department</span></div>
        </div>""", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="login-card-title">Welcome back</div>', unsafe_allow_html=True)
        st.caption("Sign in to your campus workspace or create a student account.")
        with st.container(border=True):
            sign_in_tab, register_tab = st.tabs(["Sign in", "Create account"])
            with sign_in_tab:
                role = st.radio("Login as", ["Student", "Staff"], horizontal=True)
                username = st.text_input("SRN / Staff username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                if st.button("Sign in", type="primary", use_container_width=True):
                    u = user_by_name(username.strip())
                    if u and u.get("is_active", True) and u["role"] == role.lower() and verify_pw(password, u["password_hash"]):
                        st.session_state.uid = u["id"]
                        st.session_state.last_activity = datetime.now().timestamp()
                        st.rerun()
                    else:
                        st.error("Login failed. Check your username, password and account status.")
                st.caption("Students use their SRN. Staff use their full name as the username.")
            with register_tab:
                st.subheader("Create a student account")
                st.caption("Staff accounts are created by an authorised administrator.")
                with st.form("student_registration_form"):
                    reg_name = st.text_input("Full name")
                    reg_srn = st.text_input("SRN")
                    reg_gender = st.selectbox("Gender", ["Prefer not to say", "Female", "Male", "Other"])
                    reg_course = st.text_input("Course", placeholder="e.g. BBA Business Analytics")
                    reg_year = st.selectbox("Year of study", ["Year 1", "Year 2", "Year 3", "Year 4"])
                    reg_password = st.text_input("Create password (6+ characters, letters and numbers)", type="password")
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
            elif len(new) < 6 or not any(ch.isalpha() for ch in new) or not any(ch.isdigit() for ch in new):
                st.error("Use at least 6 characters, including at least one letter and one number.")
            elif new != confirm: st.error("Passwords do not match.")
            else:
                run("UPDATE users SET password_hash=? WHERE id=?", (hash_pw(new),u["id"]))
                st.success("Password updated.")



def notify_user(user_id, title, message):
    """Create an in-app notification only. Email delivery is intentionally disabled."""
    run("INSERT INTO notifications(user_id,title,message,created_at) VALUES(?,?,?,?)",
        (user_id, title, message, datetime.now(CAMPUS_TZ).isoformat()))
    return True


def unread_notifications(user_id):
    return all_rows("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 10", (user_id,))


def free_slots(staff_id, day, exclude_appointment_id=None):
    """Return unbooked future slots, optionally ignoring the appointment being rescheduled."""
    sql = """SELECT appointment_time FROM appointments
      WHERE staff_id=? AND appointment_date=? AND status NOT IN ('Cancelled','Rejected')"""
    args = [staff_id, day]
    if exclude_appointment_id is not None:
        sql += " AND id<>?"
        args.append(exclude_appointment_id)
    busy = {r["appointment_time"] for r in all_rows(sql, tuple(args))}
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
    return genai.Client(api_key=api_key, http_options={"timeout": 12000})

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
    # One lightweight request only; avoid sequential fallback calls that double the wait.
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt,
        config={"response_mime_type": "application/json", "temperature": 0.1, "max_output_tokens": 256},
    )
    result = json.loads(response.text or "{}")
    if not isinstance(result, dict):
        raise ValueError("Unexpected AI response")
    return result


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
            {"role": "assistant", "content": "Hi! I can help you find campus support and understand the appointment process. Staff members schedule appointments for students."}
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

        render_change_confirmation("ai_pending_change", u, "floating_ai")

        with st.form("floating_ai_message_form", clear_on_submit=True):
            message = st.text_input("Message", placeholder="Ask to book an appointment…", label_visibility="collapsed")
            sent = st.form_submit_button("Send", use_container_width=True)
        if sent and message.strip():
            st.session_state.floating_ai_messages.append({"role":"user","content":message.strip()})
            try:
                with st.spinner("Campus Assistant is thinking…"):
                    intent = gemini_parse(message.strip())
                kind = (intent.get("intent") or "other").lower()
                answer = intent.get("summary") or "I understood your request."
                if kind == "book":
                    answer = "Appointments are scheduled by authorised staff. You can view scheduled meetings in My appointments or submit an issue to the Chairperson."
                elif kind == "view":
                    answer = "Your appointments are shown in the My appointments section of your dashboard."
                elif kind in ("cancel", "reschedule"):
                    answer = "Please contact the staff member or Chairperson to request a change to a staff-scheduled appointment."
                elif kind == "find_department":
                    answer = intent.get("clarifying_question") or "Tell me briefly what issue you need help with."
                else:
                    answer = intent.get("clarifying_question") or "I can help you find the right campus department or explain how to contact the Chairperson. What do you need?"
                st.session_state.floating_ai_messages.append({"role":"assistant","content":answer})
            except Exception:
                st.session_state.floating_ai_messages.append({"role":"assistant","content":"Sorry, I could not process that request. Please try again shortly, or contact the relevant department."})
            st.rerun()

@st.fragment(run_every="15s")
def student_page(u):
    st.title(f"Good to see you, {u['full_name'].split()[0]}")
    st.caption("Your campus support overview")
    today = datetime.now(CAMPUS_TZ).date().isoformat()
    summary = all_rows("""SELECT
        COUNT(*) FILTER (WHERE status IN ('Scheduled','Confirmed') AND appointment_date>=?) AS upcoming,
        COUNT(*) FILTER (WHERE status='Pending') AS pending,
        COUNT(*) FILTER (WHERE status='Completed') AS completed
        FROM appointments WHERE student_id=?""", (today,u["id"]))[0]
    unread_count = all_rows("SELECT COUNT(*) AS n FROM notifications WHERE user_id=? AND is_read=FALSE", (u["id"],))[0]["n"]
    metric_cols = st.columns(4)
    for col, label, value in zip(metric_cols, ["Upcoming", "Pending", "Completed", "Unread updates"],
                                 [summary["upcoming"], summary["pending"], summary["completed"], unread_count]):
        with col: st.metric(label, value)
    st.markdown("### Your workspace")
    notifications_tab, book_tab, appointments_tab, chair_tab = st.tabs(
        ["Notifications", "Book appointment", "My appointments", "Contact Chairperson"])
    with notifications_tab:
        notes = unread_notifications(u["id"])
        if not notes:
            st.info("No notifications yet.")
        for n in notes:
            with st.container(border=True):
                st.markdown(f"**{n['title']}**")
                st.write(n["message"])
                st.caption(n["created_at"])
                if not n["is_read"] and st.button("Mark as read", key=f"read_{n['id']}"):
                    run("UPDATE notifications SET is_read=TRUE WHERE id=? AND user_id=?", (n["id"],u["id"]))
                    st.rerun()
    with book_tab:
        st.subheader("Book an appointment")
        staff_members = all_rows("""SELECT id,full_name,department,room_no,block_name
            FROM users WHERE role='staff' AND is_active=TRUE AND is_chairperson=FALSE
            ORDER BY department,full_name""")
        if not staff_members:
            st.info("No staff members are currently available for booking.")
        else:
            staff_map = {f"{x['full_name']} — {x['department']}": x for x in staff_members}
            # Keep availability controls outside a form so changing staff/date immediately reruns
            # this fragment and recalculates free slots.
            staff_label = st.selectbox("Department / staff member", list(staff_map), key=f"student_staff_{u['id']}")
            chosen_staff = staff_map[staff_label]
            chosen_day = st.date_input("Preferred date", min_value=datetime.now(CAMPUS_TZ).date(),
                value=datetime.now(CAMPUS_TZ).date()+timedelta(days=1), key=f"student_day_{u['id']}")
            slots = free_slots(chosen_staff["id"], chosen_day.isoformat())
            chosen_slot = st.selectbox("Available time", slots if slots else ["No slots available"],
                key=f"student_slot_{u['id']}_{chosen_staff['id']}_{chosen_day.isoformat()}")
            booking_reason = st.text_area("Reason for appointment", key=f"student_reason_{u['id']}")
            book_submit = st.button("Submit booking request", type="primary", disabled=not slots,
                key=f"student_book_submit_{u['id']}")
            if book_submit:
                if not booking_reason.strip():
                    st.error("Please provide a reason for the appointment.")
                else:
                    try:
                        run("""INSERT INTO appointments
                            (student_id,staff_id,department,appointment_date,appointment_time,reason,status,created_at,booking_source)
                            VALUES(?,?,?,?,?,?,'Pending',?,'student')""",
                            (u["id"],chosen_staff["id"],chosen_staff["department"],chosen_day.isoformat(),
                             chosen_slot,booking_reason.strip(),datetime.now(CAMPUS_TZ).isoformat()))
                        notify_user(chosen_staff["id"], "New student appointment request",
                            f"{u['full_name']} ({u['srn']}) requested an appointment on {chosen_day.isoformat()} at {chosen_slot}. Reason: {booking_reason.strip()}")
                        st.success("Booking request sent. The staff member must confirm or reject it.")
                        st.rerun()
                    except psycopg.errors.UniqueViolation:
                        st.error("That slot was just taken. Please select another time.")

    with appointments_tab:
        appts = all_rows("""SELECT a.*,s.full_name staff_name,s.room_no,s.block_name FROM appointments a
          JOIN users s ON s.id=a.staff_id WHERE a.student_id=? ORDER BY a.created_at DESC, a.appointment_date DESC, a.appointment_time DESC""", (u["id"],))
        if not appts:
            st.info("No appointments have been scheduled for you yet.")
        for a in appts:
            with st.container(border=True):
                st.markdown(f"**{a['department']} — {a['staff_name']}**")
                st.write(f"{a['appointment_date']} at {a['appointment_time']} · {a['status']}")
                st.write(f"Location: {a['room_no'] or 'TBC'}, {a['block_name'] or 'TBC'}")
                st.write(f"Purpose: {a['reason']}")
                if a["resolution_status"] != "Not recorded":
                    st.write(f"**Outcome:** {a['resolution_status']}")
                    if a["follow_up"]: st.write(f"**Follow-up:** {a['follow_up']}")
                if a.get("booking_source") == "student" and a["status"] in ("Pending", "Confirmed"):
                    if st.button("Cancel my booking", key=f"student_cancel_{a['id']}"):
                        run("UPDATE appointments SET status='Cancelled' WHERE id=? AND student_id=? AND booking_source='student' AND status IN ('Pending','Confirmed')",
                            (a["id"],u["id"]))
                        notify_user(a["staff_id"], "Student cancelled appointment",
                                    f"{u['full_name']} cancelled the appointment for {a['appointment_date']} at {a['appointment_time']}.")
                        st.success("Your booking has been cancelled.")
                        st.rerun()
                if a.get("booking_source") == "staff" and a["status"] == "Scheduled":
                    with st.expander("Request a reschedule"):
                        with st.form(f"reschedule_request_{a['id']}"):
                            new_day = st.date_input("Preferred new date",
                                min_value=datetime.now(CAMPUS_TZ).date(),
                                value=datetime.now(CAMPUS_TZ).date()+timedelta(days=1),
                                key=f"reschedule_day_{a['id']}")
                            reschedule_slots = free_slots(a["staff_id"], new_day.isoformat())
                            new_time = st.selectbox("Preferred new time",
                                reschedule_slots if reschedule_slots else ["No slots available"],
                                key=f"reschedule_time_{a['id']}")
                            reschedule_reason = st.text_area("Reason for rescheduling", key=f"reschedule_reason_{a['id']}")
                            request_submit = st.form_submit_button("Send reschedule request",
                                disabled=not reschedule_slots)
                        if request_submit:
                            if not reschedule_reason.strip():
                                st.error("Please provide a reason.")
                            else:
                                run("""UPDATE appointments SET reschedule_status='Requested',
                                    reschedule_date=?,reschedule_time=?,reschedule_reason=?
                                    WHERE id=? AND student_id=? AND booking_source='staff' AND status='Scheduled'""",
                                    (new_day.isoformat(),new_time,reschedule_reason.strip(),a["id"],u["id"]))
                                notify_user(a["staff_id"], "Reschedule request from student",
                                    f"{u['full_name']} requested {new_day.isoformat()} at {new_time}. Reason: {reschedule_reason.strip()}")
                                st.success("Reschedule request sent. The appointment remains unchanged until staff responds.")
                                st.rerun()
                if a.get("reschedule_status") == "Requested":
                    st.info(f"Reschedule request awaiting staff: {a.get('reschedule_date')} at {a.get('reschedule_time')}.")
                elif a.get("reschedule_status") == "Declined":
                    st.warning("Your reschedule request was declined. The original appointment remains scheduled.")
    with chair_tab:
        st.write("Share an issue or query directly with the Chairperson.")
        with st.form("student_chairperson_concern"):
            subject = st.text_input("Subject")
            message = st.text_area("Describe your issue or query", height=140)
            submit = st.form_submit_button("Submit to Chairperson", type="primary")
        if submit:
            if not subject.strip() or not message.strip():
                st.error("Please enter both a subject and a description.")
            else:
                chair = all_rows("SELECT id FROM users WHERE role='staff' AND is_chairperson=TRUE AND is_active=TRUE LIMIT 1")
                run("""INSERT INTO student_concerns(student_id,subject,message,status,created_at,updated_at)
                       VALUES(?,?,?,'Submitted',?,?)""",
                    (u["id"],subject.strip(),message.strip(),datetime.now(CAMPUS_TZ).isoformat(),datetime.now(CAMPUS_TZ).isoformat()))
                if chair:
                    notify_user(chair[0]["id"], "New student concern",
                                f"{u['full_name']} ({u['srn']}) submitted: {subject.strip()}. Please review the Chairperson dashboard.")
                st.success("Your concern has been submitted.")
        concerns = all_rows("""SELECT * FROM student_concerns WHERE student_id=? ORDER BY created_at DESC""",(u["id"],))
        for c in concerns:
            with st.container(border=True):
                st.markdown(f"**{c['subject']}** · {c['status']}")
                st.write(c["message"])
                if c["chairperson_reply"]:
                    st.info("Chairperson response: " + c["chairperson_reply"])


@st.fragment(run_every="15s")
def staff_page(u):
    is_chair = bool(u.get("is_chairperson"))
    st.title(f"Good to see you, {u['full_name'].split()[0]}")
    st.caption("Chairperson overview" if is_chair else f"{u['department']} · Staff workspace")
    
staff_summary = all_rows("""SELECT
    COUNT(*) FILTER (
        WHERE appointment_date = CURRENT_DATE::text
        AND status NOT IN ('Cancelled','Rejected')
    ) AS today_count,
    COUNT(*) FILTER (
        WHERE status='Pending'
        AND booking_source='student'
    ) AS pending_count,
    COUNT(*) FILTER (
        WHERE status IN ('Scheduled','Confirmed')
        AND appointment_date >= CURRENT_DATE::text
    ) AS upcoming_count,
    COUNT(*) FILTER (
        WHERE status='Completed'
    ) AS completed_count
    FROM appointments
    WHERE staff_id=?""", (u["id"],))[0]

    metric_cols = st.columns(4)
    for col, label, value in zip(metric_cols, ["Today", "Pending requests", "Upcoming", "Completed"],
                                 [staff_summary["today_count"], staff_summary["pending_count"], staff_summary["upcoming_count"], staff_summary["completed_count"]]):
        with col: st.metric(label, value)
    st.markdown("### Your workspace")
    if is_chair:
        tabs = st.tabs(["Student Directory", "Schedule Appointment", "Student Concerns", "Meetings"])
        directory_tab, schedule_tab, concerns_tab, meetings_tab = tabs
    else:
        tabs = st.tabs(["Student Directory", "Schedule Appointment", "My Meetings"])
        directory_tab, schedule_tab, meetings_tab = tabs
        concerns_tab = None

    with directory_tab:
        st.subheader("Registered students")
        search = st.text_input("Search by student name or SRN", key=f"student_search_{u['id']}")
        search_term = f"%{search.strip()}%"
        count_rows = all_rows("""SELECT COUNT(*) AS total FROM users
                               WHERE role='student' AND is_active=TRUE
                               AND (LOWER(full_name) LIKE LOWER(?) OR LOWER(COALESCE(srn,'')) LIKE LOWER(?))""",
                              (search_term, search_term))
        total_students = count_rows[0]["total"] if count_rows else 0
        page_count = max(1, (total_students + 99) // 100)
        page_no = st.number_input("Directory page", min_value=1, max_value=page_count, value=1,
                                  step=1, key=f"directory_page_{u['id']}")
        students = all_rows("""SELECT id,full_name,srn,course,study_year,gender FROM users
                               WHERE role='student' AND is_active=TRUE
                               AND (LOWER(full_name) LIKE LOWER(?) OR LOWER(COALESCE(srn,'')) LIKE LOWER(?))
                               ORDER BY full_name LIMIT 100 OFFSET ?""",
                            (search_term,search_term,(int(page_no)-1)*100))
        st.caption(f"Showing {len(students)} of {total_students} matching registered students. Use the page selector to browse all records.")
        for student in students:
            with st.expander(f"{student['full_name']} · {student['srn']}"):
                st.write(f"**Course:** {student['course'] or 'Not provided'}")
                st.write(f"**Year:** {student['study_year'] or 'Not provided'}")
                st.write(f"**Gender:** {student['gender'] or 'Not provided'}")

    with schedule_tab:
        st.subheader("Schedule an appointment for a student")
        student_search = st.text_input("Find student by name or SRN", key=f"schedule_student_search_{u['id']}")
        students = all_rows("""SELECT id,full_name,srn,course,study_year FROM users
                               WHERE role='student' AND is_active=TRUE
                               AND (LOWER(full_name) LIKE LOWER(?) OR LOWER(COALESCE(srn,'')) LIKE LOWER(?))
                               ORDER BY full_name LIMIT 50""",
                            (f"%{student_search.strip()}%",f"%{student_search.strip()}%")) if student_search.strip() else []
        staff_members = all_rows("""SELECT id,full_name,department,designation,room_no,block_name
                                    FROM users WHERE role='staff' AND is_active=TRUE
                                    AND (is_chairperson=FALSE OR id=?) ORDER BY full_name""",(u["id"],))
        if not students:
            st.info("Search for a registered student by name or SRN. Register demo student accounts first if the directory is empty.")
        elif not staff_members:
            st.info("No active staff accounts are available.")
        else:
            student_map = {f"{x['full_name']} — {x['srn']}":x for x in students}
            staff_map = {f"{x['full_name']} — {x['department']}":x for x in staff_members}
            # Availability widgets are outside a form so selecting a new staff member/date
            # immediately recalculates slots. This section also refreshes every 15 seconds.
            selected_student_label = st.selectbox("Select student", list(student_map), key=f"schedule_student_select_{u['id']}")
            selected_staff_label = st.selectbox("Staff member", list(staff_map),
                index=list(staff_map).index(next((k for k,v in staff_map.items() if v["id"]==u["id"]), list(staff_map)[0])),
                key=f"schedule_staff_select_{u['id']}")
            selected_day = st.date_input("Appointment date", min_value=datetime.now(CAMPUS_TZ).date(),
                value=datetime.now(CAMPUS_TZ).date()+timedelta(days=1), key=f"schedule_day_{u['id']}")
            selected_staff = staff_map[selected_staff_label]
            slots = free_slots(selected_staff["id"], selected_day.isoformat())
            selected_slot = st.selectbox("Available time", slots if slots else ["No slots available"],
                key=f"schedule_slot_{u['id']}_{selected_staff['id']}_{selected_day.isoformat()}")
            reason = st.text_area("Meeting purpose", key=f"schedule_reason_{u['id']}")
            submit_appointment = st.button("Schedule appointment", type="primary",
                disabled=not slots, key=f"schedule_submit_{u['id']}")
            if submit_appointment:
                student = student_map[selected_student_label]
                try:
                    run("""INSERT INTO appointments(student_id,staff_id,department,appointment_date,appointment_time,reason,status,created_at)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (student["id"],selected_staff["id"],selected_staff["department"],selected_day.isoformat(),
                         selected_slot,reason.strip() or "Staff-scheduled meeting","Scheduled",datetime.now(CAMPUS_TZ).isoformat()))
                    message = (f"An appointment has been scheduled for you with {selected_staff['full_name']} "
                               f"on {selected_day.isoformat()} at {selected_slot}. "
                               f"Location: {selected_staff['room_no'] or 'TBC'}, {selected_staff['block_name'] or 'TBC'}. "
                               f"Purpose: {reason.strip() or 'Staff-scheduled meeting'}.")
                    notify_user(student["id"],"New appointment scheduled",message)
                    st.success("Appointment scheduled. The student has received an in-app notification.")
                    st.rerun()
                except psycopg.errors.UniqueViolation:
                    st.error("That slot was just taken. Refresh and choose another available time.")

    if is_chair and concerns_tab is not None:
        with concerns_tab:
            st.subheader("Student issues and queries")
            concerns = all_rows("""SELECT c.*,u.full_name student_name,u.srn,u.course,u.study_year
                FROM student_concerns c JOIN users u ON u.id=c.student_id
                ORDER BY c.created_at DESC LIMIT 300""")
            if not concerns:
                st.info("No student concerns have been submitted.")
            for c in concerns:
                with st.expander(f"{c['subject']} · {c['student_name']} ({c['srn']}) · {c['status']}"):
                    st.write(f"**Course:** {c['course']} · {c['study_year']}")
                    st.write(c["message"])
                    reply = st.text_area("Response",value=c["chairperson_reply"] or "",key=f"chair_reply_{c['id']}")
                    status = st.selectbox("Status",["Submitted","In Progress","Resolved"],
                        index=["Submitted","In Progress","Resolved"].index(c["status"]),key=f"chair_status_{c['id']}")
                    if st.button("Save response",key=f"save_concern_{c['id']}"):
                        run("UPDATE student_concerns SET chairperson_reply=?,status=?,updated_at=? WHERE id=?",
                            (reply,status,datetime.now(CAMPUS_TZ).isoformat(),c["id"]))
                        notify_user(c["student_id"],"Chairperson updated your concern",
                                    f"Your concern '{c['subject']}' is now {status}. {reply}")
                        st.success("Response saved and student notified."); st.rerun()

    with meetings_tab:
        rows = all_rows("""SELECT a.*,u.full_name student_name,u.srn,u.course,u.study_year
          FROM appointments a JOIN users u ON u.id=a.student_id
          WHERE a.staff_id=? ORDER BY a.created_at DESC, a.appointment_date DESC, a.appointment_time DESC""", (u["id"],))
        if not rows:
            st.info("No meetings scheduled yet.")
        for a in rows:
            with st.container(border=True):
                st.markdown(f"**{a['student_name']}** · {a['srn'] or 'No SRN'}")
                st.write(f"{a['appointment_date']} at {a['appointment_time']} · {a['status']}")
                st.write(f"{a['course'] or ''} · {a['study_year'] or ''}")
                st.write(f"Location: {u['room_no'] or 'TBC'}, {u['block_name'] or 'TBC'}")
                st.write(f"Purpose: {a['reason']}")
                if a.get("booking_source") == "staff" and a["status"] in ("Scheduled", "Confirmed"):
                    with st.expander("Manage this appointment"):
                        if st.button("Cancel appointment", key=f"staff_cancel_created_{a['id']}"):
                            run("""UPDATE appointments SET status='Cancelled'
                                WHERE id=? AND staff_id=? AND booking_source='staff'
                                AND status IN ('Scheduled','Confirmed')""", (a["id"],u["id"]))
                            notify_user(a["student_id"], "Appointment cancelled by staff",
                                f"Your appointment with {u['full_name']} on {a['appointment_date']} at {a['appointment_time']} has been cancelled.")
                            st.success("Appointment cancelled and student notified.")
                            st.rerun()
                        with st.form(f"staff_reschedule_created_{a['id']}"):
                            staff_new_day = st.date_input("New appointment date",
                                min_value=datetime.now(CAMPUS_TZ).date(),
                                value=datetime.now(CAMPUS_TZ).date()+timedelta(days=1),
                                key=f"staff_new_day_{a['id']}")
                            staff_new_slots = free_slots(u["id"], staff_new_day.isoformat(),
                                exclude_appointment_id=a["id"])
                            staff_new_time = st.selectbox("New available time",
                                staff_new_slots if staff_new_slots else ["No slots available"],
                                key=f"staff_new_time_{a['id']}_{staff_new_day.isoformat()}")
                            staff_change_reason = st.text_area("Reason for changing appointment",
                                key=f"staff_change_reason_{a['id']}")
                            staff_reschedule_submit = st.form_submit_button(
                                "Save new appointment time", disabled=not staff_new_slots)
                        if staff_reschedule_submit:
                            try:
                                run("""UPDATE appointments SET appointment_date=?,appointment_time=?,
                                    reason=CASE WHEN ?='' THEN reason ELSE reason || ' | Update: ' || ? END
                                    WHERE id=? AND staff_id=? AND booking_source='staff'
                                    AND status IN ('Scheduled','Confirmed')""",
                                    (staff_new_day.isoformat(),staff_new_time,staff_change_reason.strip(),
                                     staff_change_reason.strip(),a["id"],u["id"]))
                                notify_user(a["student_id"], "Appointment rescheduled by staff",
                                    f"Your appointment has been moved to {staff_new_day.isoformat()} at {staff_new_time}. "
                                    f"Location: {u['room_no'] or 'TBC'}, {u['block_name'] or 'TBC'}. "
                                    f"{('Reason: ' + staff_change_reason.strip()) if staff_change_reason.strip() else ''}")
                                st.success("Appointment rescheduled and student notified.")
                                st.rerun()
                            except psycopg.errors.UniqueViolation:
                                st.error("That time slot is no longer available. The original appointment remains unchanged.")
                if a.get("booking_source") == "student" and a["status"] == "Pending":
                    st.warning("Student booking request — awaiting your decision.")
                    c1, c2 = st.columns(2)
                    if c1.button("Confirm booking", key=f"confirm_student_booking_{a['id']}"):
                        run("UPDATE appointments SET status='Confirmed' WHERE id=? AND staff_id=? AND status='Pending' AND booking_source='student'",
                            (a["id"],u["id"]))
                        notify_user(a["student_id"], "Appointment confirmed",
                                    f"Your appointment with {u['full_name']} on {a['appointment_date']} at {a['appointment_time']} is confirmed.")
                        st.rerun()
                    if c2.button("Reject booking", key=f"reject_student_booking_{a['id']}"):
                        run("UPDATE appointments SET status='Rejected' WHERE id=? AND staff_id=? AND status='Pending' AND booking_source='student'",
                            (a["id"],u["id"]))
                        notify_user(a["student_id"], "Appointment request rejected",
                                    f"Your appointment request for {a['appointment_date']} at {a['appointment_time']} was rejected. Please choose another slot.")
                        st.rerun()
                if a.get("booking_source") == "staff" and a.get("reschedule_status") == "Requested":
                    st.warning(f"Reschedule requested: {a['reschedule_date']} at {a['reschedule_time']}. Reason: {a['reschedule_reason']}")
                    r1, r2 = st.columns(2)
                    if r1.button("Approve reschedule", key=f"approve_reschedule_{a['id']}"):
                        try:
                            run("""UPDATE appointments SET appointment_date=?,appointment_time=?,
                                reschedule_status='Approved',reschedule_date=NULL,reschedule_time=NULL,reschedule_reason=''
                                WHERE id=? AND staff_id=? AND reschedule_status='Requested'""",
                                (a["reschedule_date"],a["reschedule_time"],a["id"],u["id"]))
                            notify_user(a["student_id"], "Reschedule approved",
                                f"Your appointment has been moved to {a['reschedule_date']} at {a['reschedule_time']}.")
                            st.rerun()
                        except psycopg.errors.UniqueViolation:
                            st.error("That requested slot is no longer available. The original appointment is unchanged.")
                    if r2.button("Decline reschedule", key=f"decline_reschedule_{a['id']}"):
                        run("UPDATE appointments SET reschedule_status='Declined' WHERE id=? AND staff_id=? AND reschedule_status='Requested'",
                            (a["id"],u["id"]))
                        notify_user(a["student_id"], "Reschedule request declined",
                            "Your reschedule request was declined. Your original appointment remains scheduled.")
                        st.rerun()
                if a["status"] not in ("Completed","Cancelled","Rejected"):
                    if st.button("Mark meeting completed",key=f"complete_{a['id']}"):
                        run("UPDATE appointments SET status='Completed' WHERE id=? AND staff_id=?",(a["id"],u["id"]))
                        st.rerun()
                with st.expander("Meeting record"):
                    notes = st.text_area("Meeting notes",value=a["staff_notes"] or a["reason"],key=f"notes_{a['id']}")
                    queries = st.text_area("Queries addressed",value=a["queries_addressed"] or "",key=f"queries_{a['id']}")
                    resolution_options=["Not recorded","Resolved","Pending","Referred to another department"]
                    resolution = st.selectbox("Resolution",resolution_options,
                        index=resolution_options.index(a["resolution_status"] or "Not recorded"),key=f"resolution_{a['id']}")
                    follow = st.text_area("Follow-up action",value=a["follow_up"] or "",key=f"follow_{a['id']}")
                    if st.button("Save meeting record",key=f"save_meeting_{a['id']}"):
                        run("""UPDATE appointments SET staff_notes=?,queries_addressed=?,resolution_status=?,follow_up=?
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
        st.markdown("## ◈ Campus Agent")
        st.caption("STUDENT & STAFF WORKSPACE")
        nav_options = ["Dashboard","Profile","About"]
        page = st.radio("Workspace",nav_options)
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
