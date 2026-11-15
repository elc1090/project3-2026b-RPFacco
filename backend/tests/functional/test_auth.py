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
