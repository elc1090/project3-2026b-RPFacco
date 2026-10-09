import os
import sqlite3

from flask import Flask, jsonify
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only")

ALLOWED_ORIGINS = [
    "https://rpfacco.github.io",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app = Flask(__name__)
CORS(app, origins=ALLOWED_ORIGINS)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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

if __name__ == "__main__":
    app.run(debug=True)