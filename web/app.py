"""NotesApp - a small grades application.

Deliberately insecure teaching app for the EPITA Computer Security course.
Do not deploy this anywhere real.
"""
import os
import csv
import io
import json
import hmac
import time
import base64
import binascii
import hashlib
import ipaddress
import subprocess

import psycopg2
import psycopg2.extras
from flask import (
    Flask, request, session, redirect, url_for,
    render_template, Response, jsonify, abort,
)

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

# --- Configuration ------------------------------------------------------------
# All configuration comes from the environment (set in docker-compose.yml).

DB_HOST = os.environ.get("DB_HOST", "db")
DB_NAME = os.environ.get("DB_NAME", "notesapp")
DB_USER = os.environ.get("DB_USER", "notesapp")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "notesapp_pg_pw_2024")
JWT_SECRET = os.environ.get("JWT_SECRET", "s3cr3t")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-session-key")
NOTESAPP_SECRET_KEY = os.environ.get("NOTESAPP_SECRET_KEY")
if not NOTESAPP_SECRET_KEY:
    raise RuntimeError("NOTESAPP_SECRET_KEY must be set in the environment.")

key = base64.b64decode(os.environ["AES_KEY"])
assert len(key) == 32, "AES_KEY must decode to 32 bytes"


def decrypt_comment(text):
    if not text:
        return text
    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        return text
    if len(raw) < 12 + 16:
        return text
    try:
        return AESGCM(key).decrypt(raw[:12], raw[12:], None).decode("utf-8")
    except (InvalidTag, UnicodeDecodeError) as exc:
        raise ValueError(
            "Unable to decrypt comment; verify that AES_KEY matches the encryption key."
        ) from exc


def encrypt_comment(text):
    if not text:
        return text
    nonce = os.urandom(12)
    ct = AESGCM(key).encrypt(nonce, text.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode()


app = Flask(__name__)
app.secret_key = SECRET_KEY

LOG_FILE = os.environ.get("NOTESAPP_LOG", "/var/log/notesapp/app.log")


def log(msg):
    """Very small access log. No rotation, no policy (see flaw #14)."""
    try:
        with open(LOG_FILE, "a") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except OSError:
        pass


# --- Database -----------------------------------------------------------------
def get_db():
    conn = psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    conn.autocommit = True
    return conn


# --- Minimal JWT (deliberately weak) ------------------------------------------
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


def make_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    h = _b64url(json.dumps(header).encode())
    p = _b64url(json.dumps(payload).encode())
    signing_input = f"{h}.{p}".encode()
    sig = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url(sig)}"


def verify_jwt(token: str):
    """Decode a JWT. Accepts alg:none (no signature) and HS256 with a short key.

    This is intentionally broken (flaw #4): an attacker can forge any identity
    by setting "alg":"none", and the HS256 key is trivially guessable.
    """
    try:
        h_b64, p_b64, sig_b64 = token.split(".")
    except ValueError:
        return None
    try:
        header = json.loads(_b64url_decode(h_b64))
        payload = json.loads(_b64url_decode(p_b64))
    except Exception:
        return None

    alg = header.get("alg", "").lower()
    if alg == "none":
        # No signature verification at all.
        return payload
    if alg == "hs256":
        signing_input = f"{h_b64}.{p_b64}".encode()
        expected = _b64url(hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest())
        if hmac.compare_digest(expected, sig_b64):
            return payload
        return None
    return None


def current_identity():
    """Return the acting identity from a Bearer JWT if present, else the session."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        payload = verify_jwt(auth[7:].strip())
        if payload:
            return payload
    if "user_id" in session:
        return {"user_id": session["user_id"], "username": session.get("username"),
                "role": session.get("role")}
    return None


# --- Auth helpers -------------------------------------------------------------
def login_required(role=None):
    if "user_id" not in session:
        return False
    if role and session.get("role") != role:
        return False
    return True


def valid_ping_host(host):
    if not host or "%" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        hostname = host[:-1] if host.endswith(".") else host
        if not hostname or len(hostname) > 253:
            return False
        labels = hostname.split(".")
        return all(
            1 <= len(label) <= 63
            and label[0].isalnum()
            and label[-1].isalnum()
            and all(char.isascii() and (char.isalnum() or char == "-") for char in label)
            for label in labels
        )


# --- Routes -------------------------------------------------------------------
@app.route("/")
def index():
    if "user_id" in session:
        role = session.get("role")
        if role == "student":
            return redirect(url_for("dashboard"))
        if role == "teacher":
            return redirect(url_for("teacher"))
        if role == "admin":
            return redirect(url_for("admin"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        query = (
            "SELECT id, username, role FROM users "
            "WHERE username = %s AND password = %s"
        )
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(query, (username, password))
            row = cur.fetchone()
        except psycopg2.Error as exc:
            log(f"login query error: {exc}")
            error = "Login failed."
            row = None
        conn.close()
        if row:
            session["user_id"] = row["id"]
            session["username"] = row["username"]
            session["role"] = row["role"]
            # Issue a weak JWT the dashboard uses to call the API.
            session["token"] = make_jwt({
                "user_id": row["id"], "username": row["username"], "role": row["role"],
            })
            log(f"login success user={row['username']} role={row['role']}")
            return redirect(url_for("index"))
        if not error:
            error = "Invalid credentials."
        log(f"login failure username={username!r}")
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT n.id, n.grade, n.comment, c.name AS class_name "
        "FROM notes n JOIN classes c ON c.id = n.class_id "
        "WHERE n.student_id = %s ORDER BY c.name",
        (session["user_id"],),
    )
    notes = cur.fetchall()
    notes = [{**n, "comment": decrypt_comment(n["comment"])} for n in notes]
    conn.close()
    return render_template("dashboard.html", notes=notes, token=session.get("token"))


@app.route("/api/notes/<int:note_id>")
def api_notes(note_id):
    ident = current_identity()
    if not ident:
        return jsonify({"error": "unauthorized"}), 401
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT n.id, n.student_id, n.class_id, n.grade, n.comment, "
        "u.username AS student, c.name AS class_name, c.teacher_id "
        "FROM notes n JOIN users u ON u.id = n.student_id "
        "JOIN classes c ON c.id = n.class_id WHERE n.id = %s",
        (note_id,),
    )
    note = cur.fetchone()
    conn.close()
    if not note or not can_read_note(ident, note):
        return jsonify({"error": "not found"}), 404
    note["grade"] = float(note["grade"]) if note["grade"] is not None else None
    note["comment"] = decrypt_comment(note["comment"])
    return jsonify(note)


def can_read_note(ident, note):
    role, user_id = ident.get("role"), ident.get("user_id")
    if role == "student":
        return note["student_id"] == user_id
    if role == "teacher":
        return note["teacher_id"] == user_id
    return False


@app.route("/teacher")
def teacher():
    if not login_required("teacher"):
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, teacher_id FROM classes "
        "WHERE teacher_id = %s ORDER BY name",
        (session["user_id"],),
    )
    classes = cur.fetchall()
    cur.execute(
        "SELECT n.id, n.grade, n.comment, n.student_id, n.class_id, "
        "u.username AS student, c.name AS class_name "
        "FROM notes n JOIN users u ON u.id = n.student_id "
        "JOIN classes c ON c.id = n.class_id "
        "WHERE c.teacher_id = %s ORDER BY c.name, u.username",
        (session["user_id"],),
    )
    notes = cur.fetchall()
    notes = [{**n, "comment": decrypt_comment(n["comment"])} for n in notes]
    cur.execute(
        "SELECT DISTINCT u.id, u.username FROM users u "
        "JOIN enrollments e ON e.student_id = u.id "
        "JOIN classes c ON c.id = e.class_id "
        "WHERE u.role = 'student' AND c.teacher_id = %s ORDER BY u.username",
        (session["user_id"],),
    )
    students = cur.fetchall()
    conn.close()
    return render_template("teacher.html", classes=classes, notes=notes, students=students)


@app.route("/grades", methods=["POST"])
def grades():
    # Flaw #11: no CSRF token checked on this state-changing POST.
    if not login_required("teacher"):
        return redirect(url_for("login"))
    note_id = request.form.get("note_id", "").strip()
    student_id = request.form.get("student_id")
    class_id = request.form.get("class_id")
    grade = request.form.get("grade")
    comment = encrypt_comment(request.form.get("comment", ""))
    conn = get_db()
    cur = conn.cursor()
    if note_id:
        cur.execute(
            "SELECT c.teacher_id FROM notes n "
            "JOIN classes c ON c.id = n.class_id WHERE n.id = %s",
            (note_id,),
        )
        row = cur.fetchone()
        if not row or row["teacher_id"] != session["user_id"]:
            conn.close()
            abort(403)
        cur.execute(
            "UPDATE notes SET grade = %s, comment = %s WHERE id = %s",
            (grade, comment, note_id),
        )
    else:
        cur.execute(
            "SELECT 1 FROM classes c "
            "JOIN enrollments e ON e.class_id = c.id "
            "WHERE c.id = %s AND c.teacher_id = %s AND e.student_id = %s",
            (class_id, session["user_id"], student_id),
        )
        if not cur.fetchone():
            conn.close()
            abort(403)
        cur.execute(
            "INSERT INTO notes (student_id, class_id, grade, comment) "
            "VALUES (%s, %s, %s, %s)",
            (student_id, class_id, grade, comment),
        )
    conn.close()
    log(f"grade write by {session.get('username')} note_id={note_id or 'new'}")
    return redirect(url_for("teacher"))


@app.route("/export.csv")
def export_csv():
    if not login_required("teacher"):
        return redirect(url_for("login"))
    class_id = request.args.get("class_id")
    conn = get_db()
    cur = conn.cursor()
    if class_id:
        cur.execute(
            "SELECT u.username AS student, c.name AS class, n.grade, n.comment "
            "FROM notes n JOIN users u ON u.id = n.student_id "
            "JOIN classes c ON c.id = n.class_id "
            "WHERE n.class_id = %s AND c.teacher_id = %s "
            "ORDER BY u.username",
            (class_id, session["user_id"]),
        )
    else:
        cur.execute(
            "SELECT u.username AS student, c.name AS class, n.grade, n.comment "
            "FROM notes n JOIN users u ON u.id = n.student_id "
            "JOIN classes c ON c.id = n.class_id "
            "WHERE c.teacher_id = %s ORDER BY c.name, u.username",
            (session["user_id"],),
        )
    rows = cur.fetchall()
    rows = [{**r, "comment": decrypt_comment(r["comment"])} for r in rows]
    conn.close()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["student", "class", "grade", "comment"])
    for r in rows:
        writer.writerow([r["student"], r["class"], r["grade"], r["comment"]])
    csv_bytes = buf.getvalue().encode("utf-8")
    signature = hmac.new(
        NOTESAPP_SECRET_KEY.encode("utf-8"),
        csv_bytes,
        hashlib.sha256,
    ).hexdigest()
    return Response(
        csv_bytes, mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=grades.csv",
            "X-CSV-HMAC-SHA256": signature,
        },
    )


@app.route("/admin")
def admin():
    if not login_required("admin"):
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, teacher_id FROM users ORDER BY id")
    users = cur.fetchall()
    cur.execute("SELECT id, name, teacher_id FROM classes ORDER BY id")
    classes = cur.fetchall()
    conn.close()
    return render_template("admin.html", users=users, classes=classes,
                           ping_result=request.args.get("ping_result"))


@app.route("/admin/ping", methods=["POST"])
def admin_ping():
    if not login_required("admin"):
        return redirect(url_for("login"))
    host = request.form.get("host", "").strip()
    if not valid_ping_host(host):
        output = "Invalid host."
        return render_template("admin.html", users=_all_users(), classes=_all_classes(),
                               ping_result=output)
    try:
        result = subprocess.run(
            ["ping", "-c", "1", host],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout + result.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        log(f"admin ping failed host={host!r}: {exc}")
        output = "Ping failed."
    log(f"admin ping host={host!r}")
    return render_template("admin.html", users=_all_users(), classes=_all_classes(),
                           ping_result=output)


def _all_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, teacher_id FROM users ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows


def _all_classes():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, teacher_id FROM classes ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows


@app.route("/admin/users", methods=["POST"])
def admin_users():
    if not login_required("admin"):
        return redirect(url_for("login"))
    action = request.form.get("action")
    conn = get_db()
    cur = conn.cursor()
    if action == "create":
        cur.execute(
            "INSERT INTO users (username, password, role, teacher_id) "
            "VALUES (%s, %s, %s, %s)",
            (request.form.get("username"), request.form.get("password"),
             request.form.get("role", "student"), None),
        )
    elif action == "delete":
        cur.execute("DELETE FROM users WHERE id = %s", (request.form.get("user_id"),))
    conn.close()
    return redirect(url_for("admin"))


@app.route("/healthz")
def healthz():
    try:
        conn = get_db()
        conn.close()
        return "ok", 200
    except Exception as e:
        return f"db error: {e}", 500


if __name__ == "__main__":
    # Plain HTTP on purpose (flaw #3). Nginx + TLS is added in a later lab.
    app.run(host="0.0.0.0", port=5000, debug=True)