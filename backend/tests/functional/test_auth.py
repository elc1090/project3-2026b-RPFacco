import pytest

def test_register_creates_user(client):
    response = client.post(
        "/api/register",
        json={"email": " Ana@Example.com ", "password": "senha-segura"},
    )

    assert response.status_code == 201
    assert response.get_json()["email"] == "ana@example.com"

def test_register_rejects_same_email_in_other_case(client):
    client.post(
        "/api/register",
        json={"email": "ana@example.com", "password": "senha-segura"},
    )

    response = client.post(
        "/api/register",
        json={"email": "ANA@example.com", "password": "outra-senha"},
    )

    assert response.status_code == 409

@pytest.mark.parametrize(
    "email",
    ["anaexample", "", "a" * 250 + "@example.com"],
    ids=["sem-arroba", "vazio", "longo-demais"],
)
def test_register_invalid_email(client, email):
    response = client.post(
        "/api/register",
        json={"email": email, "password": "senha-segura"},
    )

    assert response.status_code == 400

def test_login_token_opens_me(client):
    client.post(
        "/api/register",
        json={"email": "ana@example.com", "password": "senha-segura"},
    )

    login = client.post(
        "/api/login",
        json={"email": "ana@example.com", "password": "senha-segura"},
    )
    token = login.get_json()["token"]
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})

    assert login.status_code == 200
    assert response.status_code == 200
    assert response.get_json()["email"] == "ana@example.com"

def test_login_same_answer_for_wrong_password_and_unknown_email(client):
    client.post(
        "/api/register",
        json={"email": "ana@example.com", "password": "senha-segura"},
    )

    wrong_password = client.post(
        "/api/login",
        json={"email": "ana@example.com", "password": "senha-errada"},
    )
    unknown_email = client.post(
        "/api/login",
        json={"email": "ninguem@example.com", "password": "senha-segura"},
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.get_json() == unknown_email.get_json()
