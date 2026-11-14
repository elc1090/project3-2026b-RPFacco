def test_register_creates_user(client):
    response = client.post(
        "/api/register",
        json={"email": " Ana@Example.com ", "password": "senha-segura"},
    )

    assert response.status_code == 201
    assert response.get_json()["email"] == "ana@example.com"
