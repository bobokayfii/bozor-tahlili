from auth.security import create_access_token, verify_password
from db.models import UserRow

import api.main as api_main


def test_list_users_returns_the_seeded_admin(client):
    response = client.get("/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["username"] == "test-admin"
    assert data[0]["role"] == "admin"


def test_create_user_adds_a_new_user_that_then_appears_in_the_list(client):
    response = client.post("/admin/users", json={
        "username": "jane", "password": "jane-password", "role": "user",
    })
    assert response.status_code == 201
    assert response.json()["username"] == "jane"

    list_response = client.get("/admin/users")
    usernames = {u["username"] for u in list_response.json()}
    assert "jane" in usernames


def test_create_user_with_a_taken_username_returns_409(client):
    response = client.post("/admin/users", json={
        "username": "test-admin", "password": "whatever", "role": "user",
    })
    assert response.status_code == 409


def test_create_user_as_a_non_admin_returns_403(client):
    non_admin_token = create_access_token(user_id=99, username="regular", role="user")
    response = client.post(
        "/admin/users",
        json={"username": "new-user", "password": "pw", "role": "user"},
        headers={"Authorization": f"Bearer {non_admin_token}"},
    )
    assert response.status_code == 403


def test_update_user_changes_the_role(client):
    create_response = client.post("/admin/users", json={
        "username": "jane", "password": "jane-password", "role": "user",
    })
    user_id = create_response.json()["id"]

    response = client.patch(f"/admin/users/{user_id}", json={"role": "admin"})
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_update_user_without_a_password_keeps_the_old_password(client):
    create_response = client.post("/admin/users", json={
        "username": "jane", "password": "original-password", "role": "user",
    })
    user_id = create_response.json()["id"]

    response = client.patch(f"/admin/users/{user_id}", json={"username": "jane"})
    assert response.status_code == 200

    with api_main.SessionLocal() as session:
        user = session.get(UserRow, user_id)
        assert verify_password("original-password", user.password_hash) is True


def test_update_user_with_a_taken_username_returns_409(client):
    client.post("/admin/users", json={"username": "jane", "password": "pw", "role": "user"})
    create_response = client.post("/admin/users", json={"username": "bob", "password": "pw", "role": "user"})
    bob_id = create_response.json()["id"]

    response = client.patch(f"/admin/users/{bob_id}", json={"username": "jane"})
    assert response.status_code == 409


def test_admin_cannot_demote_themselves(client):
    response = client.patch("/admin/users/1", json={"role": "user"})
    assert response.status_code == 400


def test_update_user_with_a_nonexistent_id_returns_404(client):
    response = client.patch("/admin/users/9999", json={"role": "admin"})
    assert response.status_code == 404


def test_update_a_different_user_to_the_user_role_succeeds(client):
    create_response = client.post("/admin/users", json={
        "username": "jane", "password": "jane-password", "role": "admin",
    })
    user_id = create_response.json()["id"]

    response = client.patch(f"/admin/users/{user_id}", json={"role": "user"})
    assert response.status_code == 200
    assert response.json()["role"] == "user"


def test_admin_can_rename_themselves_without_touching_role(client):
    response = client.patch("/admin/users/1", json={"username": "test-admin-renamed"})
    assert response.status_code == 200
    assert response.json()["username"] == "test-admin-renamed"


def test_create_user_with_an_invalid_role_returns_422(client):
    response = client.post("/admin/users", json={
        "username": "x", "password": "pw", "role": "superadmin",
    })
    assert response.status_code == 422


def test_update_user_with_an_invalid_role_returns_422(client):
    response = client.patch("/admin/users/1", json={"role": "superadmin"})
    assert response.status_code == 422
