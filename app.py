import os, hashlib, hmac, json, base64, time
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
import streamlit as st


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

.brand-lockup{display:flex;align-items:center;gap:12px;padding:8px 4px 18px}
.brand-mark{width:42px;height:42px;border-radius:13px;background:linear-gradient(145deg,#8db7ff,#fff);color:#1645b8;display:grid;place-items:center;font-size:25px;font-weight:900}
.brand-name{font-size:20px;font-weight:800;letter-spacing:-.04em;color:var(--ink)}
.brand-sub{font-size:11px;color:var(--muted);margin-top:2px}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#123aa7 0%,#0d2c86 65%,#102e7c 100%)!important;border-right:0!important}
[data-testid="stSidebar"] *{color:#fff!important}
[data-testid="stSidebar"] [data-testid="stRadio"] label{border-radius:12px;padding:11px 13px;margin:4px 0;color:#fff!important}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){background:linear-gradient(90deg,#3977f6,#4e83f4)!important;box-shadow:0 8px 18px rgba(0,0,0,.15)}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:rgba(255,255,255,.13)!important}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#dce7ff!important}
.sidebar-user{padding:12px;border:1px solid rgba(255,255,255,.22);border-radius:13px;background:rgba(255,255,255,.08);font-size:13px}
.sidebar-user span{color:#dce7ff!important;font-size:11px}
.notification-card{border:1px solid var(--line);background:var(--surface);border-radius:16px;padding:18px 20px;margin:10px 0;box-shadow:var(--shadow)}
.notification-card h4{margin:0 0 7px 0;font-size:16px}
.notification-meta{font-size:12px;color:var(--muted)}
.dashboard-heading{font-size:36px;font-weight:850;letter-spacing:-.05em;color:var(--ink);margin:8px 0 2px}
.dashboard-subtitle{font-size:16px;color:var(--muted);margin-bottom:22px}
.quick-panel{border:1px solid var(--line);border-radius:18px;padding:20px;background:linear-gradient(145deg,var(--surface),var(--surface-2));min-height:250px}
@media(max-width:800px){.dashboard-heading{font-size:28px}}


/* Dashboard visual treatment */
.block-container{max-width:1600px;padding:1.35rem 1.65rem 2.5rem}
[data-testid="stSidebar"]{width:285px!important}
[data-testid="stSidebar"]>div:first-child{padding:1.25rem 1rem 1rem}
.brand-mark{background:linear-gradient(145deg,#fff,#a9caff)!important;box-shadow:0 8px 24px rgba(0,0,0,.16)}
.brand-name{color:#fff!important;font-size:22px}
.brand-sub{color:#dce8ff!important}
.dashboard-topline{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.dashboard-heading{font-size:clamp(30px,3vw,42px);font-weight:850;letter-spacing:-.055em;line-height:1.08;margin:8px 0 5px}
.dashboard-subtitle{font-size:16px;margin:0 0 22px;color:var(--muted)}
.metric-tile{border:1px solid var(--line);border-radius:18px;padding:15px 18px;background:linear-gradient(135deg,var(--surface),var(--surface-2));box-shadow:0 10px 26px rgba(20,45,100,.07);min-height:112px}
.metric-tile .metric-label{font-size:13px;font-weight:700;color:var(--muted)}
.metric-tile .metric-value{font-size:31px;font-weight:850;color:var(--ink);line-height:1.15;margin-top:5px}
.notification-item{border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin:10px 0;background:var(--surface);box-shadow:0 7px 22px rgba(25,50,100,.055)}
.notification-item.unread{border-left:4px solid #3977f6}
.notification-title{font-weight:800;font-size:16px;color:var(--ink);margin-bottom:5px}
.notification-body{font-size:13px;color:var(--muted);line-height:1.5}
.notification-time{font-size:11px;color:var(--muted);margin-top:8px}
.quick-card{overflow:hidden;border:1px solid #b8d0ff;border-radius:20px;background:linear-gradient(145deg,#eaf2ff,#cfe1ff);box-shadow:0 12px 30px rgba(38,86,180,.13);padding:0}
.quick-card-head{padding:18px 20px 8px;color:#10285e}
.quick-card-head h3{font-size:22px;font-weight:850;margin:0;color:#10285e}
.quick-card-head p{font-size:13px;color:#3f5688;margin:4px 0}
.quick-card img{width:100%;height:230px;object-fit:cover;display:block}
.quick-card-foot{margin:0 14px 14px;padding:14px 16px;border-radius:15px;background:rgba(255,255,255,.86);color:#122b65;display:flex;gap:12px;align-items:center}
.quick-card-foot strong{display:block;font-size:14px}
.quick-card-foot span{font-size:12px;color:#43577f}
.stButton>button{transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease}
.stButton>button:hover{transform:translateY(-2px);box-shadow:0 8px 18px rgba(34,80,170,.12)}
[data-theme="dark"] .metric-tile,[data-theme="dark"] .notification-item{background:linear-gradient(145deg,#121d31,#172640);border-color:#304363}
[data-theme="dark"] .quick-card{background:linear-gradient(145deg,#182b4b,#213b66);border-color:#3b5b8c}
[data-theme="dark"] .quick-card-head h3{color:#f4f7ff}
[data-theme="dark"] .quick-card-head p{color:#c5d7fa}
[data-theme="dark"] .quick-card-foot{background:rgba(10,20,40,.9);color:#f4f7ff}
[data-theme="dark"] .quick-card-foot span{color:#c5d7fa}
@media(max-width:900px){.block-container{padding:1rem .8rem 2rem}.dashboard-heading{font-size:29px}}


.block-container{max-width:1600px;padding:1.15rem 1.65rem 2.5rem}
[data-testid="stSidebar"]{width:285px!important;background:linear-gradient(180deg,#173fb4 0%,#10318e 58%,#0b286f 100%)!important;border-right:0!important}
[data-testid="stSidebar"]>div:first-child{padding:1.15rem 1rem 1rem}
.brand-lockup{padding:10px 5px 20px;gap:13px}
.brand-mark{width:48px;height:48px;border-radius:15px;background:linear-gradient(145deg,#fff,#c6dcff)!important;color:#1744b8!important;display:grid;place-items:center;font-size:27px;box-shadow:0 8px 24px rgba(0,0,0,.18)}
.brand-name{font-size:22px!important;color:#fff!important}
.brand-sub{font-size:11px;color:#e0eaff!important}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#dce7ff!important}
[data-testid="stSidebar"] [data-testid="stRadio"] label{padding:11px 13px;border-radius:12px;margin:4px 0;color:#fff!important}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){background:linear-gradient(90deg,#3977f6,#4e83f4)!important;box-shadow:0 8px 18px rgba(0,0,0,.15)}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:rgba(255,255,255,.14)!important}
.sidebar-footer-note{position:relative;margin-top:30px;padding:16px 7px 0;border-top:1px solid rgba(255,255,255,.22);font-size:12px;color:#dce7ff}
[data-testid="stPopover"] button{border-radius:14px!important}
[data-testid="stPopoverBody"]{min-width:220px}
[data-testid="stHorizontalBlock"]{align-items:center}
.stButton>button{transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease}
.stButton>button:hover{transform:translateY(-1px);box-shadow:0 8px 18px rgba(34,80,170,.12)}
.quick-card{min-height:420px}
.login-hero{position:relative!important;isolation:isolate!important;background-image:none!important}
.login-hero .login-bg-image{position:absolute!important;inset:0!important;width:100%!important;height:100%!important;object-fit:cover!important;z-index:0!important;border-radius:24px!important}
.login-hero:before{z-index:1!important}
.login-hero > *:not(.login-bg-image){position:relative!important;z-index:2!important}
.header-clearance{height:66px!important;margin-bottom:-66px!important}
.profile-identity{display:flex!important;align-items:center!important;gap:10px!important;min-height:48px!important}
.profile-avatar{width:42px!important;height:42px!important;border-radius:50%!important;display:inline-flex!important;align-items:center!important;justify-content:center!important;background:linear-gradient(145deg,#4e7cff,#1745d5)!important;color:#fff!important;font-size:17px!important;font-weight:800!important;flex:0 0 42px!important}
[data-testid="stSidebar"] [data-testid="stButton"] button{display:flex!important;align-items:center!important;justify-content:flex-start!important;gap:12px!important;text-align:left!important;padding:9px 13px!important;min-height:44px!important;border-radius:12px!important}
[data-testid="stSidebar"] [data-testid="stButton"] button [data-testid="stIconMaterial"]{font-size:21px!important;color:#fff!important}
[data-testid="stSidebar"] [data-testid="stButton"] button p{font-size:14px!important;font-weight:600!important}
"""
_bg_path = Path(__file__).with_name("campus_login_bg.png")
_bg64 = base64.b64encode(_bg_path.read_bytes()).decode("ascii") if _bg_path.exists() else ""
_CSS = _CSS.replace("</style>", f'.login-hero {{ background-image:linear-gradient(180deg,rgba(5,18,43,.05),rgba(5,18,43,.76)),url("data:image/png;base64,{_bg64}") !important; }}\n</style>')
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
        st.markdown(f"""<div class="login-hero">
          <img class="login-bg-image" src="data:image/png;base64,{_bg64}" alt="University campus">
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
    back_col, title_col = st.columns([1, 5], vertical_alignment="center")
    with back_col:
        if st.button("← Home", key="profile_back_home"):
            st.session_state.active_page = "Dashboard"
            st.rerun()
    with title_col:
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

def student_page(u, section="Book appointment"):
    # Summary cards are reserved for the Dashboard only.
    page_titles = {
        "Book appointment": "Book an appointment",
        "My appointments": "My appointments",
        "Contact Chairperson": "Contact Chairperson",
        "Notifications": "Notifications",
    }
    st.title(page_titles.get(section, section))
    if section == "Notifications":
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
    elif section == "Book appointment":
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

    elif section == "My appointments":
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
    elif section == "Contact Chairperson":
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


def staff_page(u, section="My Meetings"):
    # Summary cards are reserved for the Dashboard only.
    st.title(section)
    if section == "Student Directory":
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

    elif section == "Schedule Appointment":
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

    elif is_chair and section == "Student Concerns":
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

    elif section == "My Meetings":
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



def notifications_page(u):
    st.markdown('<div class="dashboard-heading">Notifications</div><div class="dashboard-subtitle">Stay updated on appointments, requests and campus support.</div>', unsafe_allow_html=True)
    rows = all_rows("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (u["id"],))
    if not rows:
        st.info("You're all caught up. No notifications yet.")
        return
    for n in rows:
        with st.container(border=True):
            left, right = st.columns([5, 1])
            with left:
                st.markdown(f"**{n['title']}**")
                st.write(n["message"])
                st.caption(n["created_at"])
                if not n["is_read"]:
                    st.caption("● Unread")
            with right:
                if not n["is_read"] and st.button("Mark as read", key=f"notification_read_{u['id']}_{n['id']}"):
                    run("UPDATE notifications SET is_read=TRUE WHERE id=? AND user_id=?", (n["id"],u["id"]))
                    st.rerun()


def _dashboard_metrics(u):
    today = datetime.now(CAMPUS_TZ).date().isoformat()
    if u["role"] == "student":
        row = all_rows("""SELECT
            COUNT(*) FILTER (WHERE status IN ('Scheduled','Confirmed') AND appointment_date>=?) AS upcoming,
            COUNT(*) FILTER (WHERE status='Pending') AS pending,
            COUNT(*) FILTER (WHERE status='Completed') AS completed
            FROM appointments WHERE student_id=?""", (today,u["id"]))[0]
    else:
        row = all_rows("""SELECT
            COUNT(*) FILTER (WHERE appointment_date=? AND status NOT IN ('Cancelled','Rejected')) AS upcoming,
            COUNT(*) FILTER (WHERE status='Pending' AND booking_source='student') AS pending,
            COUNT(*) FILTER (WHERE status='Completed') AS completed
            FROM appointments WHERE staff_id=?""", (today,u["id"]))[0]
    unread = all_rows("SELECT COUNT(*) AS n FROM notifications WHERE user_id=? AND is_read=FALSE", (u["id"],))[0]["n"]
    return row, unread



def _render_dashboard(u):
    from html import escape
    row, unread = _dashboard_metrics(u)
    full_name = escape(str(u["full_name"]))
    subtitle = "Your campus support overview"

    st.markdown(
        f'<div class="ref-welcome"><div><h1>Good to see you, {full_name}</h1>'
        f'<p>{subtitle}</p></div><span class="welcome-spark" aria-hidden="true">'
        '<i></i><i></i><i></i></span></div>',
        unsafe_allow_html=True,
    )

    metrics = [
        ("Upcoming" if u["role"] == "student" else "Today", row["upcoming"], '<svg viewBox="0 0 32 32"><rect x="5" y="7" width="22" height="21" rx="3"/><path d="M10 4v6M22 4v6M5 13h22M11 18h3M18 18h3M11 23h3"/></svg>', "blue"),
        ("Pending", row["pending"], '<svg viewBox="0 0 32 32"><path d="M8 4h16M8 28h16M9 5c0 6 2 7 7 11-5 4-7 5-7 11M23 5c0 6-2 7-7 11 5 4 7 5 7 11"/></svg>', "amber"),
        ("Completed", row["completed"], '<svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="12"/><path d="m10 16 4 4 8-9"/></svg>', "green"),
        ("Unread updates", unread, '<svg viewBox="0 0 32 32"><path d="M7 23h18l-2-3v-6a7 7 0 0 0-14 0v6zM13 27a3 3 0 0 0 6 0"/></svg>', "violet"),
    ]
    cols = st.columns(4, gap="small")
    for col, (label, value, symbol, tone) in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="ref-metric {tone}"><div class="ref-metric-icon">{symbol}</div>'
                f'<div class="ref-metric-copy"><span>{label}</span><strong>{value}</strong></div>'
                f'<i></i></div>',
                unsafe_allow_html=True,
            )

    st.write("")
    left, right = st.columns([2.08, 1], gap="medium")
    notes = all_rows(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 3",
        (u["id"],),
    )
    with left:
        st.markdown(
            '<div class="ref-section-title"><span class="ref-section-icon">♧</span><div>'
            '<h2>Notifications</h2><p>Stay updated on your appointments and requests</p></div></div>',
            unsafe_allow_html=True,
        )
        if not notes:
            st.markdown('<div class="ref-empty">You’re all caught up. No notifications yet.</div>', unsafe_allow_html=True)
        for n in notes:
            title = escape(str(n.get("title") or "Update"))
            message = escape(str(n.get("message") or ""))
            created = escape(str(n.get("created_at") or ""))
            lower = title.lower()
            if "cancel" in lower or "reject" in lower:
                tone, glyph = "red", '<svg viewBox="0 0 32 32"><rect x="5" y="7" width="22" height="21" rx="3"/><path d="M10 4v6M22 4v6M5 13h22m7 5 6 6m0-6-6 6"/></svg>' 
            elif "resched" in lower or "pending" in lower:
                tone, glyph = "amber", '<svg viewBox="0 0 32 32"><rect x="5" y="7" width="22" height="21" rx="3"/><path d="M10 4v6M22 4v6M5 13h22M16 17v5l4 2"/></svg>' 
            elif "schedule" in lower or "confirm" in lower or "approved" in lower:
                tone, glyph = "green", '<svg viewBox="0 0 32 32"><rect x="5" y="7" width="22" height="21" rx="3"/><path d="M10 4v6M22 4v6M5 13h22m6 6 4 4 8-9"/></svg>' 
            else:
                tone, glyph = "blue", '<svg viewBox="0 0 32 32"><rect x="5" y="7" width="22" height="21" rx="3"/><path d="M10 4v6M22 4v6M5 13h22"/></svg>' 
            is_unread = not n["is_read"]
            with st.container(key=f"ref_notice_row_{tone}_{n['id']}"):
                c1, c2 = st.columns([5.2, 1.0], vertical_alignment="center")
                with c1:
                    st.markdown(
                        f'<div class="ref-notice-inline">'
                        f'<div class="ref-notice-icon">{glyph}</div><div class="ref-notice-content">'
                        f'<div class="ref-notice-heading">{"<b class=ref-unread-dot></b>" if is_unread else ""}{title}</div>'
                        f'<div class="ref-notice-message">{message}</div>'
                        f'<div class="ref-notice-time">▦ &nbsp;{created}</div></div></div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    if is_unread and st.button("Mark as read", key=f"dash_mark_read_{u['id']}_{n['id']}"):
                        run("UPDATE notifications SET is_read=TRUE WHERE id=? AND user_id=?", (n["id"], u["id"]))
                        st.rerun()

    with right:
        art_name = "campus_dashboard_art.png"
        art_path = Path(__file__).with_name(art_name)
        if art_path.exists():
            encoded = base64.b64encode(art_path.read_bytes()).decode("ascii")
            st.markdown(
                '<div class="ref-quick-card"><div class="ref-quick-head">'
                '<span class="ref-quick-icon">▱</span><div><h2>Quick overview</h2>'
                '<p>A quick look at your campus activity</p></div></div>'
                f'<img class="ref-campus-image" src="data:image/png;base64,{encoded}" alt="Campus building">'
                '<div class="ref-quick-foot"><span class="ref-cap">◆</span><div>'
                '<strong>Your campus, connected</strong><small>Appointments and support<br>in one place.</small>'
                '</div><b>›</b></div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="ref-quick-card"><h2>Quick overview</h2><p>Your campus, connected.</p></div>', unsafe_allow_html=True)


def student_dashboard(u):
    _render_dashboard(u)


def staff_dashboard(u):
    _render_dashboard(u)



def apply_interface_theme(dark_mode: bool):
    """Apply the app's own complete colour palette, independent of browser settings."""
    if dark_mode:
        css = """
        <style>
        :root{color-scheme:dark;--canvas:#0b1428;--surface:#111f37;--surface-2:#1a2b49;--ink:#f4f7ff;--muted:#bdc9df;--line:#2b4164;--brand:#78a0ff;--brand-strong:#a9c1ff;--brand-soft:#1c3157;--shadow:0 10px 28px rgba(0,0,0,.28)}
        [data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"]{background:var(--canvas)!important;color:var(--ink)!important}
        [data-testid="stHeader"]{background:rgba(11,20,40,.94)!important}
        [data-testid="stSidebar"]{background:linear-gradient(180deg,#1744bd 0%,#123a9e 58%,#102f80 100%)!important}
        [data-testid="stSidebar"] [data-testid="stButton"] button{background:transparent!important;color:#fff!important;border-color:transparent!important}
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]{background:linear-gradient(90deg,#3977f6,#4e83f4)!important;color:#fff!important}
        [data-testid="stSidebar"] [data-testid="stButton"] button p,[data-testid="stSidebar"] [data-testid="stButton"] button span,[data-testid="stSidebar"] [data-testid="stButton"] button svg{color:#fff!important;fill:#fff!important}
        h1,h2,h3,h4,h5,p,label,[data-testid="stMarkdownContainer"],[data-testid="stCaptionContainer"],[data-testid="stMetricLabel"],.dashboard-heading,.notification-title{color:var(--ink)!important}
        [data-testid="stCaptionContainer"],.dashboard-subtitle,.notification-body,.notification-time,.notification-meta{color:var(--muted)!important}
        [data-testid="stVerticalBlockBorderWrapper"],[data-testid="stMetric"],[data-testid="stExpander"],.metric-tile,.notification-item,.notification-card,.quick-panel{background:var(--surface)!important;border-color:var(--line)!important;color:var(--ink)!important}
        [data-testid="stForm"],[data-testid="stForm"]>div,[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stForm"]{background:var(--surface)!important;color:var(--ink)!important;border-color:var(--line)!important}
        [data-testid="stForm"] p,[data-testid="stForm"] label,[data-testid="stForm"] [data-testid="stMarkdownContainer"]{color:var(--ink)!important}
        /* Inputs, form fields and disabled fields must never keep the light-theme surface. */
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input,
        [data-baseweb="input"]>div,
        [data-baseweb="base-input"],
        [data-baseweb="select"]>div,
        [data-baseweb="textarea"]>div,
        [data-baseweb="datepicker"] input,
        [data-baseweb="calendar"]{background:#172943!important;background-color:#172943!important;border-color:#456080!important;color:#f4f7ff!important}
        input,textarea,[data-baseweb="select"] *,[data-baseweb="input"] *,[data-baseweb="textarea"] *{color:#f4f7ff!important;-webkit-text-fill-color:#f4f7ff!important}
        input::placeholder,textarea::placeholder{color:#aebdd4!important;-webkit-text-fill-color:#aebdd4!important;opacity:1!important}
        [data-testid="stTextInput"] label,[data-testid="stTextArea"] label,
        [data-testid="stSelectbox"] label,[data-testid="stRadio"] label,
        [data-testid="stCheckbox"] label,[data-testid="stDateInput"] label,
        [data-testid="stNumberInput"] label{color:#e5edff!important}
        [data-testid="stPopoverBody"],[data-baseweb="popover"],[data-baseweb="menu"],
        [role="dialog"],[data-testid="stTooltipContent"]{background:#111f37!important;color:#f4f7ff!important;border:1px solid #2b4164!important}
        [data-testid="stPopoverBody"] *,[data-baseweb="popover"] *,[data-baseweb="menu"] *,
        [role="dialog"] *{color:#f4f7ff!important}
        [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTextInput"] input,
        [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTextArea"] textarea{background:#172943!important}
        [data-testid="stTabs"] [data-baseweb="tab-list"]{background:var(--surface-2)!important;border-color:var(--line)!important}
        [data-testid="stTabs"] button[role="tab"]{color:var(--muted)!important}
        [data-testid="stTabs"] button[aria-selected="true"]{background:#29466f!important;color:#fff!important}
        .stButton>button,[data-testid="stFormSubmitButton"] button{background:#1b3150!important;border-color:#365071!important;color:var(--ink)!important}
        .stButton>button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{background:#315deb!important;color:#fff!important}
        .quick-card{background:linear-gradient(145deg,#182b4b,#213b66)!important;border-color:#3b5b8c!important}
        .quick-card-head h3{color:#f4f7ff!important}.quick-card-head p{color:#c5d7fa!important}
        .quick-card-foot{background:rgba(10,20,40,.92)!important;color:#f4f7ff!important}
        .quick-card-foot span{color:#c5d7fa!important}
        hr{border-color:var(--line)!important}
        
.header-clearance{height:66px;margin-bottom:-66px;pointer-events:none}
.profile-identity{display:flex;align-items:center;gap:10px;min-height:48px;white-space:nowrap}
.profile-avatar{width:42px;height:42px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(145deg,#4e7cff,#1745d5);color:#fff!important;font-size:17px;font-weight:800;box-shadow:0 4px 12px rgba(35,83,210,.25);flex:0 0 42px}
.profile-copy{display:flex;flex-direction:column;line-height:1.15}
.profile-copy strong{font-size:14px;color:var(--ink)!important;font-weight:800}
.profile-copy small{font-size:12px;color:var(--muted)!important;margin-top:3px}
[data-testid="stSidebar"] [data-testid="stButton"]{margin:4px 0}
[data-testid="stSidebar"] [data-testid="stButton"] button{justify-content:flex-start;text-align:left;border:1px solid transparent!important;background:transparent!important;color:#fff!important;min-height:43px;padding:8px 13px!important;border-radius:12px!important;font-weight:600!important;box-shadow:none!important}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover{background:rgba(255,255,255,.13)!important;border-color:rgba(255,255,255,.12)!important;transform:translateX(2px)}
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]{background:linear-gradient(90deg,#3977f6,#4e83f4)!important;border-color:rgba(255,255,255,.12)!important;box-shadow:0 7px 18px rgba(0,0,0,.16)!important}
[data-testid="stSidebar"] [data-testid="stButton"] button p{color:#fff!important}
[data-testid="stPopover"]>button{min-width:38px!important;width:38px!important;height:42px!important;padding:0!important;border-radius:12px!important}
@media(max-width:900px){.header-clearance{height:48px;margin-bottom:-48px}.profile-avatar{width:36px;height:36px;flex-basis:36px}}

</style>"""
    else:
        css = """
        <style>
        :root{color-scheme:light;--canvas:#f3f6fc;--surface:#fff;--surface-2:#edf3fc;--ink:#101d3d;--muted:#52627f;--line:#d7e2f3;--brand:#315deb;--brand-strong:#1645b8;--brand-soft:#eaf0ff;--shadow:0 10px 28px rgba(20,45,100,.07)}
        [data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"]{background:var(--canvas)!important;color:var(--ink)!important}
        [data-testid="stHeader"]{background:rgba(243,246,252,.94)!important}
        h1,h2,h3,h4,h5,p,label,[data-testid="stMarkdownContainer"],[data-testid="stCaptionContainer"],[data-testid="stMetricLabel"],.dashboard-heading,.notification-title{color:var(--ink)}
        [data-testid="stCaptionContainer"],.dashboard-subtitle,.notification-body,.notification-time,.notification-meta{color:var(--muted)}
        [data-testid="stVerticalBlockBorderWrapper"],[data-testid="stMetric"],[data-testid="stExpander"],.metric-tile,.notification-item,.notification-card,.quick-panel{background:var(--surface);border-color:var(--line);color:var(--ink)}
        [data-baseweb="input"]>div,[data-baseweb="select"]>div,[data-baseweb="textarea"]>div{background:#fff;border-color:var(--line)}
        input,textarea,[data-baseweb="select"] *{color:var(--ink)}
        .stButton>button,[data-testid="stFormSubmitButton"] button{background:#fff;border-color:var(--line);color:var(--ink)}
        .stButton>button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{background:#315deb;color:#fff}
        /* Keep the sidebar royal blue in light mode: inactive links are transparent, never white cards. */
        [data-testid="stSidebar"]{background:linear-gradient(180deg,#1744bd 0%,#123a9e 58%,#102f80 100%)!important}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p{color:#fff!important}
        [data-testid="stSidebar"] [data-testid="stButton"]{margin:5px 0!important}
        [data-testid="stSidebar"] [data-testid="stButton"] button{
            background:transparent!important;background-color:transparent!important;
            color:#fff!important;-webkit-text-fill-color:#fff!important;
            border:1px solid transparent!important;border-radius:13px!important;
            box-shadow:none!important;min-height:45px!important;
            justify-content:flex-start!important;text-align:left!important;
            font-weight:650!important;padding:9px 14px!important
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button p,
        [data-testid="stSidebar"] [data-testid="stButton"] button span,
        [data-testid="stSidebar"] [data-testid="stButton"] button svg{color:#fff!important;fill:#fff!important}
        [data-testid="stSidebar"] [data-testid="stButton"] button:hover{
            background:rgba(255,255,255,.14)!important;border-color:rgba(255,255,255,.18)!important;
            transform:translateX(2px)!important
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]{
            background:linear-gradient(90deg,#3977f6,#4e83f4)!important;
            border-color:rgba(255,255,255,.18)!important;color:#fff!important;
            box-shadow:0 7px 18px rgba(0,0,0,.16)!important
        }
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] p,
        [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] span{color:#fff!important}
        [data-testid="stSidebar"] [data-testid="stButton"] button:focus:not(:active){outline:2px solid rgba(255,255,255,.55)!important}
        [data-testid="stSidebar"] [data-testid="stDivider"]{border-color:rgba(255,255,255,.24)!important}
        </style>"""
    st.markdown(css, unsafe_allow_html=True)





def apply_reference_dashboard_styles(dark_mode):
    """Reference-matched dashboard styling shared by student and staff views."""
    light_sidebar = Path(__file__).with_name("campus_sidebar_art_light.png")
    dark_sidebar = Path(__file__).with_name("campus_sidebar_art_dark.png")
    sidebar_path = light_sidebar
    sidebar_bg = ""
    if sidebar_path.exists():
        sidebar_b64 = base64.b64encode(sidebar_path.read_bytes()).decode("ascii")
        sidebar_bg = f'url("data:image/png;base64,{sidebar_b64}")'
    css = """
    <style>
    .block-container{max-width:1700px;padding-top:1.15rem;padding-bottom:2rem}
    .ref-welcome{display:flex;align-items:flex-start;gap:14px;margin:16px 0 22px}
    .ref-welcome h1{font-size:clamp(30px,3vw,42px);font-weight:850;letter-spacing:-.05em;line-height:1.08;margin:0;color:var(--ink)!important}
    .ref-welcome p{font-size:17px;margin:7px 0 0;color:var(--muted)!important}
    .welcome-spark{color:#1760f5;font-size:27px;font-weight:900;letter-spacing:-8px;transform:rotate(-28deg);margin:0 0 0 2px}
    .ref-metric{height:112px;position:relative;overflow:hidden;display:flex;align-items:center;gap:15px;padding:16px 18px;border-radius:19px;border:1px solid var(--line);background:linear-gradient(140deg,var(--surface),var(--surface-2));box-shadow:var(--shadow);isolation:isolate}
    .ref-metric:after{content:"";position:absolute;right:-18px;bottom:-39px;width:132px;height:78px;border-radius:100% 0 0 0;transform:rotate(-7deg);z-index:-1;opacity:.8}
    .ref-metric.blue:after{background:linear-gradient(135deg,#d8edff,#7fc4ff)}
    .ref-metric.amber:after{background:linear-gradient(135deg,#fff0d8,#ffc47b)}
    .ref-metric.green:after{background:linear-gradient(135deg,#d7f7e9,#8de2c3)}
    .ref-metric.violet:after{background:linear-gradient(135deg,#e9e1ff,#b7a1ff)}
    .ref-metric-icon{height:64px;width:64px;flex:0 0 64px;border-radius:17px;display:grid;place-items:center;font-size:31px;font-weight:800}
    .ref-metric.blue .ref-metric-icon{background:#dceeff;color:#0758dc}
    .ref-metric.amber .ref-metric-icon{background:#fff0df;color:#df8500}
    .ref-metric.green .ref-metric-icon{background:#dcf5eb;color:#078b50}
    .ref-metric.violet .ref-metric-icon{background:#eee8ff;color:#7046df}
    .ref-metric-copy{display:flex;flex-direction:column;gap:3px;z-index:1}
    .ref-metric-copy span{font-size:14px;font-weight:750;color:var(--ink)}
    .ref-metric-copy strong{font-size:34px;line-height:1;font-weight:850;color:var(--ink)}
    .ref-section-title{display:flex;align-items:center;gap:15px;margin:8px 0 20px}
    .ref-section-icon{width:62px;height:62px;border-radius:17px;background:var(--brand-soft);color:var(--brand-strong);display:grid;place-items:center;font-size:32px}
    .ref-section-title h2{font-size:28px;font-weight:850;letter-spacing:-.035em;color:var(--ink);margin:0}
    .ref-section-title p{font-size:14px;color:var(--muted);margin:2px 0 0}
    .ref-notice{min-height:130px;display:flex;align-items:center;gap:16px;padding:15px 18px;margin:7px 0 12px;border:1px solid;border-radius:17px;background:var(--surface);box-shadow:var(--shadow)}
    .ref-notice-inline{min-height:104px;display:flex;align-items:center;gap:16px;padding:10px 8px;background:transparent}
    div[class*="st-key-ref_notice_row_"]{border:1px solid #9bc4ff;border-radius:17px;padding:5px 10px;margin:7px 0 12px;background:var(--surface);box-shadow:var(--shadow)}
    div[class*="st-key-ref_notice_row_red_"]{border-color:#ff9eae;background:linear-gradient(110deg,rgba(255,235,239,.75),var(--surface))}
    div[class*="st-key-ref_notice_row_amber_"]{border-color:#ffd17a;background:linear-gradient(110deg,rgba(255,246,226,.78),var(--surface))}
    div[class*="st-key-ref_notice_row_green_"]{border-color:#83dfbd;background:linear-gradient(110deg,rgba(228,250,240,.8),var(--surface))}
    div[class*="st-key-ref_notice_row_blue_"]{border-color:#9bc4ff}
    .ref-notice-inline .ref-notice-icon{width:66px;height:66px;flex:0 0 66px;border-radius:18px;display:grid;place-items:center;font-size:32px;font-weight:800}
    .ref-notice-inline .ref-notice-content{min-width:0;flex:1}
    div[class*="st-key-ref_notice_row_"] [data-testid="stButton"] button{min-height:40px!important;padding:7px 12px!important;white-space:nowrap!important;border:1px solid #4e83f4!important;background:rgba(255,255,255,.72)!important;color:#1459e8!important;font-size:13px!important}
    div[class*="st-key-ref_notice_row_"] [data-testid="stHorizontalBlock"]{gap:.5rem!important}

    .ref-notice.red{border-color:#ff9eae;background:linear-gradient(110deg,rgba(255,235,239,.75),var(--surface))}
    .ref-notice.amber{border-color:#ffd17a;background:linear-gradient(110deg,rgba(255,246,226,.78),var(--surface))}
    .ref-notice.green{border-color:#83dfbd;background:linear-gradient(110deg,rgba(228,250,240,.8),var(--surface))}
    .ref-notice.blue{border-color:#9bc4ff}
    .ref-notice-icon{width:66px;height:66px;flex:0 0 66px;border-radius:18px;display:grid;place-items:center;font-size:32px;font-weight:800}
    .ref-notice.red .ref-notice-icon{background:#ffe5e9;color:#ed3434}
    .ref-notice.amber .ref-notice-icon{background:#fff0d9;color:#e18a00}
    .ref-notice.green .ref-notice-icon{background:#ddf6eb;color:#079253}
    .ref-notice.blue .ref-notice-icon{background:#e0edff;color:#145ee8}
    .ref-notice-content{min-width:0;flex:1}
    .ref-notice-heading{font-size:17px;font-weight:850;line-height:1.25;color:var(--ink);margin-bottom:5px}
    .ref-unread-dot{display:inline-block;width:12px;height:12px;border-radius:50%;background:#ed3d35;margin-right:10px}
    .ref-notice-message{font-size:13px;line-height:1.45;color:var(--ink)}
    .ref-notice-time{font-size:12px;color:var(--muted);margin-top:9px}
    .ref-empty{padding:22px;border:1px solid var(--line);border-radius:16px;background:var(--surface);color:var(--muted)}
    .ref-quick-card{overflow:hidden;border:1px solid #b7d0ff;border-radius:20px;background:linear-gradient(145deg,#f7faff,#dceaff);box-shadow:var(--shadow);padding:17px}
    .ref-quick-head{display:flex;align-items:center;gap:13px;margin-bottom:13px}
    .ref-quick-icon{width:58px;height:58px;flex:0 0 58px;border-radius:16px;background:#e0ecff;color:#1559dd;display:grid;place-items:center;font-size:32px}
    .ref-quick-head h2{font-size:24px;font-weight:850;letter-spacing:-.04em;color:#0c1c4d;margin:0}
    .ref-quick-head p{font-size:13px;color:#304b82;margin:2px 0 0}
    .ref-campus-image{width:100%!important;max-width:100%!important;height:250px!important;object-fit:cover!important;display:block;margin:0!important;border:0!important;border-radius:0!important}
    .ref-quick-foot{display:flex;align-items:center;gap:12px;padding:13px 15px;margin-top:10px;border:1px solid #d1e0ff;border-radius:16px;background:rgba(255,255,255,.88);color:#10285e}
    .ref-cap{width:52px;height:52px;flex:0 0 52px;border-radius:14px;background:#dceaff;color:#1559dd;display:grid;place-items:center;font-size:27px}
    .ref-quick-foot div{flex:1}
    .ref-quick-foot strong{display:block;font-size:15px}
    .ref-quick-foot small{display:block;font-size:12px;line-height:1.35;color:#38517f}
    .ref-quick-foot>b{font-size:28px;color:#1459e8}
    .ref-notice+.stHorizontalBlock{margin-top:-1px}
    section[data-testid="stSidebar"]{width:318px!important;min-width:318px!important;max-width:318px!important;flex:0 0 318px!important}
    [data-testid="stSidebar"]{width:318px!important;min-width:318px!important;max-width:318px!important;background-color:#123a9e!important;background-image:linear-gradient(180deg,rgba(12,55,172,.08),rgba(5,37,127,.08)),SIDEBAR_IMAGE!important;background-position:center bottom!important;background-size:318px 372px!important;background-repeat:no-repeat!important}
    [data-testid="stSidebar"]>div:first-child{width:100%!important}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"]{background:transparent!important}
    /* Reference-style two-button theme switch. */
    .st-key-theme_light_button button,.st-key-theme_dark_button button{min-height:38px!important;height:38px!important;border-radius:999px!important;padding:0!important;font-size:20px!important;line-height:1!important;border:1px solid #8aa9ee!important;box-shadow:none!important}
    .st-key-theme_light_button button[kind="primary"],.st-key-theme_dark_button button[kind="primary"]{background:#fff!important;color:#1557df!important;border-color:#7ea2ff!important;box-shadow:0 3px 12px rgba(35,85,190,.18)!important}
    .st-key-theme_light_button button[kind="secondary"],.st-key-theme_dark_button button[kind="secondary"]{background:#8ea5d4!important;color:#fff!important}
    @media(max-width:950px){section[data-testid="stSidebar"],[data-testid="stSidebar"]{width:270px!important;min-width:270px!important;max-width:270px!important;background-size:270px 316px!important}.ref-metric{padding:12px;gap:9px}.ref-metric-icon{width:48px;height:48px;flex-basis:48px}.ref-metric-copy strong{font-size:28px}.ref-section-title h2{font-size:23px}}
    </style>
    """
    css = css.replace("SIDEBAR_IMAGE", sidebar_bg or "none")
    if dark_mode:
        css = css.replace(
            "</style>",
            """
            .ref-metric{background:linear-gradient(145deg,#10213f,#172c50);border-color:#355381}
            .ref-metric.blue:after{background:linear-gradient(135deg,#164b91,#277de1)}
            .ref-metric.amber:after{background:linear-gradient(135deg,#76501f,#c17a2c)}
            .ref-metric.green:after{background:linear-gradient(135deg,#145b4b,#1aa985)}
            .ref-metric.violet:after{background:linear-gradient(135deg,#49377d,#7553d9)}
            .ref-metric.blue .ref-metric-icon{background:#173f77;color:#75baff}
            .ref-metric.amber .ref-metric-icon{background:#51402b;color:#ffb72d}
            .ref-metric.green .ref-metric-icon{background:#174d46;color:#52e0b3}
            .ref-metric.violet .ref-metric-icon{background:#3d3473;color:#c4aaff}
            .ref-notice{background:linear-gradient(120deg,#15233d,#111f37)!important}
            div[class*="st-key-ref_notice_row_"]{background:linear-gradient(120deg,#15233d,#111f37)!important;border-color:#45618a!important}
            div[class*="st-key-ref_notice_row_red_"]{border-color:#bd435f!important;background:linear-gradient(110deg,#2a1c32,#111f37)!important}
            div[class*="st-key-ref_notice_row_amber_"]{border-color:#bd852d!important;background:linear-gradient(110deg,#30291f,#111f37)!important}
            div[class*="st-key-ref_notice_row_green_"]{border-color:#279c83!important;background:linear-gradient(110deg,#15352f,#111f37)!important}
            div[class*="st-key-ref_notice_row_"] [data-testid="stButton"] button{background:#102c58!important;color:#fff!important;border-color:#4c83ff!important}
            .ref-notice-inline .ref-notice-heading,.ref-notice-inline .ref-notice-message{color:#f4f7ff!important}
            .ref-notice-inline .ref-notice-time{color:#c4d4ee!important}
            .ref-notice.red{border-color:#bd435f;background:linear-gradient(110deg,#2a1c32,#111f37)!important}
            .ref-notice.amber{border-color:#bd852d;background:linear-gradient(110deg,#30291f,#111f37)!important}
            .ref-notice.green{border-color:#279c83;background:linear-gradient(110deg,#15352f,#111f37)!important}
            .ref-notice.red .ref-notice-icon{background:#4a2a3d;color:#ff7777}
            .ref-notice.amber .ref-notice-icon{background:#4a3a27;color:#ffbd42}
            .ref-notice.green .ref-notice-icon{background:#17483f;color:#5ce3b7}
            .ref-notice.blue .ref-notice-icon{background:#1b3c6c;color:#81baff}
            .ref-quick-card{border-color:#365d9b;background:linear-gradient(145deg,#10264a,#142f5c)}
            .ref-quick-head h2{color:#f4f7ff}.ref-quick-head p{color:#c2d5f6}
            .ref-quick-icon{background:#1d4178;color:#9ac3ff}
            .ref-quick-foot{border-color:#365d9b;background:rgba(12,31,64,.9);color:#f4f7ff}
            .ref-quick-foot small{color:#c6d8f8}.ref-cap{background:#1d4178;color:#9ac3ff}
            </style>"""
        )

    st.markdown(css + """
    <style>
    [data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"]{background:#F2F6FF!important;color:#10204B!important}
    [data-testid="stHeader"]{background:rgba(242,246,255,.94)!important}
    [data-testid="stSidebar"]{background-color:#0D3AAE!important;background-position:center bottom!important;background-size:318px 260px!important;background-repeat:no-repeat!important}
    .ref-welcome h1{color:#0B1744!important}
    .welcome-spark{display:flex;align-items:flex-start;gap:5px;width:42px;margin:0 0 0 4px;padding-top:2px;transform:none}
    .welcome-spark i{display:block;width:4px;height:22px;background:#1760F5;border-radius:4px;transform:rotate(18deg)}
    .welcome-spark i:nth-child(2){height:31px;margin-top:-7px}
    .welcome-spark i:nth-child(3){height:24px;margin-top:-1px}
    .ref-metric-icon svg,.ref-notice-inline .ref-notice-icon svg{width:34px;height:34px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
    .profile-copy strong{color:#10204B!important}.profile-copy small{color:#304B82!important}
    </style>
    """, unsafe_allow_html=True)


def main():
    init_db()
    if "uid" not in st.session_state:
        login_page()
        return
    u = get_user()
    if not u:
        st.session_state.clear()
        st.rerun()
        return

    now = datetime.now().timestamp()
    if now - st.session_state.get("last_activity", now) > 300:
        st.session_state.clear()
        st.warning("Signed out after inactivity. Please log in again.")
        st.rerun()
        return
    st.session_state.last_activity = now

    # Fixed to the approved light reference design; theme switch removed.
    st.session_state.app_dark_mode = False

    # Role-specific sidebar navigation; profile and sign-out live in the top-right menu.
    if u["role"] == "student":
        nav_items = ["Dashboard", "Notifications", "Book appointment",
                     "My appointments", "Contact Chairperson", "About"]
    else:
        nav_items = ["Dashboard", "Notifications", "Student Directory",
                     "Schedule Appointment", "My Meetings"]
        if u.get("is_chairperson"):
            nav_items.append("Student Concerns")
        nav_items.append("About")

    with st.sidebar:
        st.markdown(
            '<div class="brand-lockup"><div class="brand-mark">🎓</div>'
            '<div><div class="brand-name">Campus Agent</div>'
            '<div class="brand-sub">Campus Appointment Agent</div></div></div>',
            unsafe_allow_html=True,
        )
        st.divider()
        unread = all_rows(
            "SELECT COUNT(*) AS n FROM notifications WHERE user_id=? AND is_read=FALSE",
            (u["id"],),
        )[0]["n"]
        labels = [f"Notifications  ·  {unread}" if x == "Notifications" and unread else x for x in nav_items]
        if "active_page" not in st.session_state or st.session_state.get("active_user_id") != u["id"]:
            st.session_state.active_page = "Dashboard"
            st.session_state.active_user_id = u["id"]
        current_label = next(
            (lab for lab in labels if lab.split("  ·")[0] == st.session_state.active_page),
            labels[0],
        )
        nav_icons = {
            "Dashboard": ":material/home:",
            "Notifications": ":material/notifications:",
            "Book appointment": ":material/calendar_month:",
            "My appointments": ":material/layers:",
            "Contact Chairperson": ":material/groups:",
            "Student Directory": ":material/groups:",
            "Schedule Appointment": ":material/event_available:",
            "My Meetings": ":material/calendar_today:",
            "Student Concerns": ":material/forum:",
            "About": ":material/info:",
        }
        # Material Symbols icons match the clean outline style in the reference.
        for item, display_label in zip(nav_items, labels):
            active = st.session_state.active_page == item
            icon = nav_icons.get(item, ":material/circle:")
            if st.button(
                display_label,
                icon=icon,
                key=f"side_nav_{u['id']}_{item.replace(' ', '_')}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state.active_page = item
                st.rerun()

    # Global header: lowered to clear Streamlit's top toolbar.
    initials = "".join(part[0] for part in u["full_name"].split()[:2]).upper()
    first_name = u["full_name"].split()[0]
    if u["role"] == "student":
        role_label = " · ".join(str(v) for v in (u.get("course"), u.get("study_year")) if v) or "Student"
    else:
        role_label = str(u.get("department") or "Department not set")
    header_full_name = __import__("html").escape(str(u["full_name"]))
    header_subtitle = __import__("html").escape(role_label)
    st.markdown('<div class="header-clearance"></div>', unsafe_allow_html=True)
    h_spacer, h_bell, h_identity, h_menu = st.columns(
        [8.15, 0.75, 2.05, 0.45], vertical_alignment="center"
    )
    apply_interface_theme(False)
    apply_reference_dashboard_styles(False)
    with h_bell:
        if st.button(f"🔔 {unread if unread else ''}", key="header_notifications", help="Open notifications"):
            st.session_state.active_page = "Notifications"
            st.rerun()
    with h_identity:
        st.markdown(
            f'<div class="profile-identity"><span class="profile-avatar">{initials}</span>'
            f'<span class="profile-copy"><strong>{first_name}</strong><small>{role_label}</small></span></div>',
            unsafe_allow_html=True,
        )
    with h_menu:
        with st.popover("⌄", use_container_width=True):
            st.markdown(f"**{u['full_name']}**")
            st.caption(role_label)
            st.divider()
            if st.button("👤  Profile", use_container_width=True, key="header_profile"):
                st.session_state.active_page = "Profile"
                st.rerun()
            if st.button("↪  Sign out", use_container_width=True, key="header_signout"):
                st.session_state.clear()
                st.rerun()

    page = st.session_state.active_page
    if page == "Profile":
        profile_page(u)
    elif page == "About":
        st.markdown('<div class="dashboard-heading">About Campus Agent</div>', unsafe_allow_html=True)
        st.markdown("A campus support workspace for appointments, department coordination and student follow-up.")
        st.info("Prototype for demonstration. Use fictional data until formally approved by the university.")
        st.markdown("### Contact & Support")
        st.write("For questions or assistance with the Campus Appointment Agent:")
        st.markdown("**Email:** xxxx@gmail.com")
        st.markdown("**Project contacts**")
        st.markdown("- Sushmitha Vobilini · 987xxxxx")
        st.markdown("- Samshitha Srikanth · 765xxxxx")
    elif page == "Notifications":
        notifications_page(u)
    elif page == "Dashboard":
        if u["role"] == "student":
            student_dashboard(u)
        else:
            staff_dashboard(u)
    else:
        if u["role"] == "student":
            student_page(u, page)
        else:
            staff_page(u, page)


if __name__ == "__main__":
    main()
