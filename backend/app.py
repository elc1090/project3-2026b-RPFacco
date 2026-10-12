import os
import sqlite3
import zipfile
from datetime import datetime, timedelta, timezone

import jwt
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
MAX_UPLOAD_BYTES = 300 * 1024 * 1024

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only")

ALLOWED_ORIGINS = [
    "https://rpfacco.github.io",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

DOCS_URL = "/api/docs"
OPENAPI_URL = "/api/openapi.yaml"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
CORS(app, origins=ALLOWED_ORIGINS)
app.register_blueprint(get_swaggerui_blueprint(DOCS_URL, OPENAPI_URL), url_prefix=DOCS_URL)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()

init_db()

@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})

@app.get(OPENAPI_URL)
def openapi():
    return send_from_directory(BASE_DIR, "openapi.yaml", mimetype="text/yaml")

@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}

    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or "@" not in email or len(email) > 254:
        return jsonify({"error": "Email inválido"}), 400

    if type(password) is not str or len(password) < 8:
        return jsonify({"error": "A senha deve ter pelo menos 8 caracteres"}), 400

    password_hash = generate_password_hash(password)

    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash),
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"error": "Este email já está cadastrado"}), 409
    finally:
        conn.close()

    return jsonify({"id": user_id, "email": email}), 201

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}

    email = str(data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or type(password) is not str:
        return jsonify({"error": "Email ou senha incorretos"}), 401

    conn = get_db()
    user = conn.execute(
        "SELECT id, email, password_hash FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Email ou senha incorretos"}), 401

    token = jwt.encode(
        {
            "sub": str(user["id"]),
            "exp": datetime.now(timezone.utc) + timedelta(hours=24),
        },
        SECRET_KEY,
        algorithm="HS256",
    )

    return jsonify({"token": token})

def current_user_id():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None

    token = header[len("Bearer "):]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None

    return int(payload["sub"])

@app.get("/api/me")
def me():
    user_id = current_user_id()
    if user_id is None:
        return jsonify({"error": "Não autenticado"}), 401

    conn = get_db()
    user = conn.execute(
        "SELECT id, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if user is None:
        return jsonify({"error": "Não autenticado"}), 401

    return jsonify(dict(user))

@app.post("/api/panoramas")
def create_panorama():
    user_id = current_user_id()
    if user_id is None:
        return jsonify({"error": "Não autenticado"}), 401

    file = request.files.get("file")
    if file is None:
        return jsonify({"error": "Envie o arquivo no campo 'file'"}), 400

    if not zipfile.is_zipfile(file.stream):
        return jsonify({"error": "O arquivo precisa ser um ZIP"}), 400
    file.stream.seek(0)

    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO panoramas (user_id) VALUES (?)",
            (user_id,),
        )
        conn.commit()
        panorama_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"error": "Não autenticado"}), 401
    finally:
        conn.close()

    folder = os.path.join(STORAGE_DIR, str(panorama_id))
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, "input.zip"))

    return jsonify({"id": panorama_id, "status": "pending"}), 201

if __name__ == "__main__":
    app.run(debug=True)