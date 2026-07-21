import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
import os

# --- PATH SETUP ---
# Database stays in root for easy access
DB_FILE = Path(__file__).resolve().parents[1] / "safetwin.db"

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------------------------------
# INITIALIZATION
# -------------------------------------------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Users Table
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE, name TEXT, email TEXT UNIQUE,
        password TEXT, secret_code TEXT, admin INTEGER DEFAULT 0
    )""")

    # Industrial Monitoring Sessions
    cur.execute("""CREATE TABLE IF NOT EXISTS monitor_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT, site_id TEXT, location TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # Hazard Detection Logs
    cur.execute("""CREATE TABLE IF NOT EXISTS hazard_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        hazard_level TEXT,
        gas_ppm REAL,
        description TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(session_id) REFERENCES monitor_sessions(id)
    )""")

    # Work Permits Table (Permit Intelligence)
    cur.execute("""CREATE TABLE IF NOT EXISTS work_permits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        permit_id TEXT UNIQUE,
        permit_type TEXT,
        equipment_id TEXT,
        location TEXT,
        start_time DATETIME,
        end_time DATETIME,
        authorized_by TEXT,
        status TEXT DEFAULT 'ACTIVE',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(equipment_id) REFERENCES equipment(id)
    )""")

    # Equipment Registry (for Knowledge Graph)
    cur.execute("""CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_id TEXT UNIQUE,
        name TEXT,
        location TEXT,
        equipment_type TEXT,
        maintenance_interval_days INTEGER,
        last_maintenance DATETIME,
        risk_category TEXT
    )""")

    # Incident Reports (for Pattern Analysis)
    cur.execute("""CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT UNIQUE,
        site_id TEXT,
        location TEXT,
        incident_type TEXT,
        severity_level TEXT,
        description TEXT,
        root_cause TEXT,
        corrective_actions TEXT,
        regulatory_reference TEXT,
        reported_by TEXT,
        reported_at DATETIME,
        resolved_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # Near-Miss Events
    cur.execute("""CREATE TABLE IF NOT EXISTS near_miss_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT UNIQUE,
        location TEXT,
        description TEXT,
        potential_risk TEXT,
        reported_by TEXT,
        reported_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # Compliance Audit Logs
    cur.execute("""CREATE TABLE IF NOT EXISTS compliance_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        audit_id TEXT UNIQUE,
        audit_type TEXT,
        regulation_reference TEXT,
        check_description TEXT,
        status TEXT,
        severity TEXT,
        corrective_action TEXT,
        due_date DATETIME,
        completed_date DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    # Permit-Equipment-Hazard Relationships (Knowledge Graph)
    cur.execute("""CREATE TABLE IF NOT EXISTS permit_hazard_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        permit_id TEXT,
        equipment_id TEXT,
        hazard_type TEXT,
        risk_level TEXT,
        mitigation_strategy TEXT,
        FOREIGN KEY(permit_id) REFERENCES work_permits(permit_id),
        FOREIGN KEY(equipment_id) REFERENCES equipment(equipment_id)
    )""")
    
    conn.commit()
    conn.close()

# -------------------------------------------------
# USER AUTHENTICATION
# -------------------------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, name, email, password, secret_code):
    try:
        with get_conn() as conn:
            conn.execute("INSERT INTO users (username, name, email, password, secret_code) VALUES (?,?,?,?,?)",
                         (username, name, email, hash_password(password), secret_code))
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(email, password):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, hash_password(password)),
        ).fetchone()

def username_exists(username):
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        return row is not None
    
def get_email_by_username(username):
    with get_conn() as conn:
        row = conn.execute("SELECT email FROM users WHERE username=?", (username,)).fetchone()
        return row['email'] if row else None


def verify_secret_code(username, secret_code):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT secret_code FROM users WHERE username=?",
            (username,),
        ).fetchone()
        if not row:
            return False
        return row["secret_code"] == secret_code


def update_password(email, new_password):
    try:
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET password=? WHERE email=?",
                (hash_password(new_password), email),
            )
        return True, "Password updated successfully"
    except sqlite3.Error as exc:
        return False, str(exc)
# -------------------------------------------------
# SAFETY LOGGING
# -------------------------------------------------
def log_hazard(session_id, hazard_level, gas_ppm, description):
    with get_conn() as conn:
        conn.execute("INSERT INTO hazard_logs (session_id, hazard_level, gas_ppm, description) VALUES (?,?,?,?)",
                     (session_id, hazard_level, gas_ppm, description))

def fetch_hazard_history(session_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM hazard_logs WHERE session_id=? ORDER BY timestamp DESC", 
                            (session_id,)).fetchall()

# -------------------------------------------------
# WORK PERMIT MANAGEMENT
# -------------------------------------------------
def create_work_permit(permit_id, permit_type, equipment_id, location, start_time, end_time, authorized_by):
    """Create a new work permit"""
    try:
        with get_conn() as conn:
            conn.execute("""INSERT INTO work_permits 
                (permit_id, permit_type, equipment_id, location, start_time, end_time, authorized_by, status)
                VALUES (?,?,?,?,?,?,?,?)""",
                (permit_id, permit_type, equipment_id, location, start_time, end_time, authorized_by, 'ACTIVE'))
        return True
    except sqlite3.IntegrityError:
        return False

def get_active_permits(location=None):
    """Fetch all active permits, optionally filtered by location"""
    with get_conn() as conn:
        if location:
            return conn.execute(
                "SELECT * FROM work_permits WHERE status='ACTIVE' AND location=? ORDER BY start_time DESC",
                (location,)).fetchall()
        return conn.execute("SELECT * FROM work_permits WHERE status='ACTIVE' ORDER BY start_time DESC").fetchall()

def get_permit_by_id(permit_id):
    """Fetch a specific permit"""
    with get_conn() as conn:
        return conn.execute("SELECT * FROM work_permits WHERE permit_id=?", (permit_id,)).fetchone()

def update_permit_status(permit_id, status):
    """Update permit status (ACTIVE, COMPLETED, CANCELLED)"""
    with get_conn() as conn:
        conn.execute("UPDATE work_permits SET status=? WHERE permit_id=?", (status, permit_id))

# -------------------------------------------------
# EQUIPMENT REGISTRY
# -------------------------------------------------
def register_equipment(equipment_id, name, location, equipment_type, maintenance_interval_days, risk_category):
    """Register new equipment in the system"""
    try:
        with get_conn() as conn:
            conn.execute("""INSERT INTO equipment 
                (equipment_id, name, location, equipment_type, maintenance_interval_days, risk_category)
                VALUES (?,?,?,?,?,?)""",
                (equipment_id, name, location, equipment_type, maintenance_interval_days, risk_category))
        return True
    except sqlite3.IntegrityError:
        return False

def get_equipment_by_location(location):
    """Get all equipment at a location"""
    with get_conn() as conn:
        return conn.execute("SELECT * FROM equipment WHERE location=?", (location,)).fetchall()

def get_equipment_by_id(equipment_id):
    """Get specific equipment"""
    with get_conn() as conn:
        return conn.execute("SELECT * FROM equipment WHERE equipment_id=?", (equipment_id,)).fetchone()

def update_equipment_maintenance(equipment_id, maintenance_date):
    """Update last maintenance date"""
    with get_conn() as conn:
        conn.execute("UPDATE equipment SET last_maintenance=? WHERE equipment_id=?", 
                     (maintenance_date, equipment_id))

# -------------------------------------------------
# INCIDENT MANAGEMENT & PATTERN ANALYSIS
# -------------------------------------------------
def log_incident(incident_id, site_id, location, incident_type, severity_level, 
                 description, reported_by, regulatory_reference=None):
    """Log a new incident"""
    try:
        with get_conn() as conn:
            conn.execute("""INSERT INTO incidents 
                (incident_id, site_id, location, incident_type, severity_level, description, 
                 reported_by, reported_at, regulatory_reference)
                VALUES (?,?,?,?,?,?,?,datetime('now'),?)""",
                (incident_id, site_id, location, incident_type, severity_level, description, reported_by, regulatory_reference))
        return True
    except sqlite3.IntegrityError:
        return False

def get_incidents_by_location(location, limit=50):
    """Get incident history for a location"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM incidents WHERE location=? ORDER BY reported_at DESC LIMIT ?",
            (location, limit)).fetchall()

def get_incident_patterns(location, days=90):
    """Get incident patterns for risk assessment"""
    with get_conn() as conn:
        return conn.execute("""
            SELECT incident_type, COUNT(*) as count, severity_level 
            FROM incidents 
            WHERE location=? AND reported_at > datetime('now', '-' || ? || ' days')
            GROUP BY incident_type, severity_level
            ORDER BY count DESC
        """, (location, days)).fetchall()

def log_near_miss(event_id, location, description, potential_risk, reported_by):
    """Log near-miss event"""
    try:
        with get_conn() as conn:
            conn.execute("""INSERT INTO near_miss_events 
                (event_id, location, description, potential_risk, reported_by, reported_at)
                VALUES (?,?,?,?,?,datetime('now'))""",
                (event_id, location, description, potential_risk, reported_by))
        return True
    except sqlite3.IntegrityError:
        return False

def get_near_miss_events(location, days=30):
    """Get recent near-miss events"""
    with get_conn() as conn:
        return conn.execute("""
            SELECT * FROM near_miss_events 
            WHERE location=? AND reported_at > datetime('now', '-' || ? || ' days')
            ORDER BY reported_at DESC
        """, (location, days)).fetchall()

# -------------------------------------------------
# COMPLIANCE AUDIT
# -------------------------------------------------
def log_compliance_check(audit_id, audit_type, regulation_reference, check_description, 
                        status, severity, due_date, corrective_action=None):
    """Log compliance audit check"""
    try:
        with get_conn() as conn:
            conn.execute("""INSERT INTO compliance_audit 
                (audit_id, audit_type, regulation_reference, check_description, 
                 status, severity, due_date, corrective_action)
                VALUES (?,?,?,?,?,?,?,?)""",
                (audit_id, audit_type, regulation_reference, check_description, 
                 status, severity, due_date, corrective_action))
        return True
    except sqlite3.IntegrityError:
        return False

def get_compliance_issues(status='OPEN'):
    """Get all compliance issues with given status"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM compliance_audit WHERE status=? ORDER BY due_date ASC",
            (status,)).fetchall()

def get_compliance_by_regulation(regulation_reference):
    """Get compliance checks for a specific regulation"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM compliance_audit WHERE regulation_reference=? ORDER BY created_at DESC",
            (regulation_reference,)).fetchall()

# -------------------------------------------------
# KNOWLEDGE GRAPH - PERMIT-HAZARD RELATIONSHIPS
# -------------------------------------------------
def link_permit_hazard(permit_id, equipment_id, hazard_type, risk_level, mitigation_strategy):
    """Create knowledge graph link between permit, equipment, and hazard"""
    try:
        with get_conn() as conn:
            conn.execute("""INSERT INTO permit_hazard_links 
                (permit_id, equipment_id, hazard_type, risk_level, mitigation_strategy)
                VALUES (?,?,?,?,?)""",
                (permit_id, equipment_id, hazard_type, risk_level, mitigation_strategy))
        return True
    except Exception as e:
        print(f"Error linking permit-hazard: {e}")
        return False

def get_permit_hazards(permit_id):
    """Get all hazards associated with a permit"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM permit_hazard_links WHERE permit_id=?",
            (permit_id,)).fetchall()

def get_equipment_hazard_profile(equipment_id):
    """Get all hazards associated with equipment"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM permit_hazard_links WHERE equipment_id=?",
            (equipment_id,)).fetchall()

# -------------------------------------------------
# HELPER FUNCTIONS FOR EXISTING UI
# -------------------------------------------------
def get_name_by_username(username):
    """Get user's name by username"""
    with get_conn() as conn:
        row = conn.execute("SELECT name FROM users WHERE username=?", (username,)).fetchone()
        return row['name'] if row else "User"

def unique_id(prefix=""):
    """Generate a unique ID"""
    import uuid
    unique_part = str(uuid.uuid4())[:8]
    return f"{prefix}_{unique_part}" if prefix else unique_part

def db_id(session_id):
    """Get database ID from session - returns session_id if valid"""
    if session_id is None:
        return None
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM monitor_sessions WHERE id=?", (session_id,)).fetchone()
        return session_id if row else None

def insert_session(username, site_id, location):
    """Insert a new monitoring session"""
    try:
        with get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO monitor_sessions (username, site_id, location) VALUES (?,?,?)",
                (username, site_id, location)
            )
            return cursor.lastrowid
    except Exception:
        return None


def fetch_sessions():
    """Compatibility helper for admin dashboard UI."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, username, site_id, location, created_at FROM monitor_sessions ORDER BY id DESC"
        ).fetchall()


def fetch_session_by_id(session_id):
    """Compatibility helper for admin dashboard UI."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, username, site_id, location, created_at FROM monitor_sessions WHERE id=?",
            (session_id,)
        ).fetchone()


def insert_analysis_result(session_id, description, result_type="analysis"):
    """Insert analysis result as hazard log entry"""
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO hazard_logs (session_id, hazard_level, description) VALUES (?,?,?)",
                (session_id, result_type, description)
            )
        return True
    except Exception:
        return False

def fetch_analysis_results_by_session(session_id):
    """Fetch all analysis results for a session"""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM hazard_logs WHERE session_id=? ORDER BY timestamp DESC",
            (session_id,)
        ).fetchall()

# Initialize on import
init_db()