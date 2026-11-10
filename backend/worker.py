import glob
import os
import shutil
import subprocess
import time

from app import STORAGE_DIR, UPLOAD_DIR, get_db
from stitch import HUGIN_IMAGE, stitch

POLL_SECONDS = 5
KEEP_INPUT_DAYS = 7
CLEANUP_SECONDS = 3600

def docker_ready():
    try:
        subprocess.run(["docker", "image", "inspect", HUGIN_IMAGE], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return True

def reset_interrupted():
    conn = get_db()
    conn.execute("UPDATE panoramas SET status = 'pending' WHERE status = 'processing'")
    conn.commit()
    conn.close()

def claim_next():
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM panoramas WHERE status = 'pending' ORDER BY id LIMIT 1"
        ).fetchone()
        if row is None:
            return None

        cursor = conn.execute(
            "UPDATE panoramas SET status = 'processing' WHERE id = ? AND status = 'pending'",
            (row["id"],),
        )
        conn.commit()
        return row["id"] if cursor.rowcount == 1 else None
    finally:
        conn.close()

def set_status(panorama_id, status):
    conn = get_db()
    conn.execute("UPDATE panoramas SET status = ? WHERE id = ?", (status, panorama_id))
    conn.commit()
    conn.close()

def process(panorama_id):
    print(f"Panorâmica {panorama_id}: costurando...", flush=True)
    started = time.time()
    folder = os.path.join(STORAGE_DIR, str(panorama_id))
    try:
        stitch(folder)
    except subprocess.CalledProcessError as error:
        print(f"Panorâmica {panorama_id}: o Hugin falhou\n{error.stderr}", flush=True)
        set_status(panorama_id, "failed")
        return
    except Exception as error:
        print(f"Panorâmica {panorama_id}: falhou ({error})", flush=True)
        set_status(panorama_id, "failed")
        return

    set_status(panorama_id, "done")
    print(f"Panorâmica {panorama_id}: pronta em {time.time() - started:.0f} s", flush=True)

def delete_old_inputs():
    if not os.path.isdir(STORAGE_DIR):
        return
    limit = time.time() - KEEP_INPUT_DAYS * 86400
    for name in os.listdir(STORAGE_DIR):
        pano = os.path.join(STORAGE_DIR, name, "pano.jpg")
        archive = os.path.join(STORAGE_DIR, name, "input.zip")
        if os.path.exists(archive) and os.path.exists(pano) and os.path.getmtime(pano) < limit:
            os.remove(archive)

def delete_stale_uploads():
    limit = time.time() - 86400
    for folder in glob.glob(os.path.join(UPLOAD_DIR, "*", "*")):
        if os.path.getmtime(folder) < limit:
            shutil.rmtree(folder, ignore_errors=True)

def main():
    if not docker_ready():
        print(f"O Docker não está rodando ou a imagem {HUGIN_IMAGE} não existe. Abra o Docker Desktop e tente de novo.")
        return

    reset_interrupted()
    print("Worker rodando. Ctrl+C para parar.", flush=True)
    last_cleanup = 0
    while True:
        if time.time() - last_cleanup >= CLEANUP_SECONDS:
            delete_old_inputs()
            delete_stale_uploads()
            last_cleanup = time.time()
        panorama_id = claim_next()
        if panorama_id is None:
            time.sleep(POLL_SECONDS)
            continue
        process(panorama_id)

if __name__ == "__main__":
    main()
