import io
import zipfile

def login_as(client, email):
    client.post("/api/register", json={"email": email, "password": "senha-segura"})
    token = client.post("/api/login", json={"email": email, "password": "senha-segura"}).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}

def capture_zip():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("metadata.json", "{}")
    buffer.seek(0)
    return buffer

def test_other_user_cannot_see_panorama(client):
    ana = login_as(client, "ana@example.com")
    bruno = login_as(client, "bruno@example.com")
    upload = client.post(
        "/api/panoramas",
        data={"file": (capture_zip(), "360_photos.zip")},
        headers=ana,
        content_type="multipart/form-data",
    )
    panorama_id = upload.get_json()["id"]

    ana_image = client.get(f"/api/panoramas/{panorama_id}/image", headers=ana)
    bruno_image = client.get(f"/api/panoramas/{panorama_id}/image", headers=bruno)
    bruno_gallery = client.get("/api/panoramas", headers=bruno)

    assert upload.status_code == 201
    assert ana_image.status_code == 409
    assert bruno_image.status_code == 404
    assert bruno_gallery.get_json() == []
