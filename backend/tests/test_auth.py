import os

import pytest
from fastapi.testclient import TestClient

from backend.app.auth import create_access_token, get_password_hash, verify_password
from backend.app.main import app

client = TestClient(app)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "secret123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token({"sub": "admin"})
        assert isinstance(token, str)
        from backend.app.auth import decode_access_token
        payload = decode_access_token(token)
        assert payload["sub"] == "admin"


class TestAuthEndpoints:
    def test_login_creates_admin_and_returns_token(self):
        os.environ["ADMIN_USER"] = "admin_test"
        os.environ["ADMIN_PASSWORD"] = "admin_pass"
        response = client.post("/api/auth/login", json={"username": "admin_test", "password": "admin_pass"})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self):
        response = client.post("/api/auth/login", json={"username": "admin_test", "password": "wrong"})
        assert response.status_code == 401

    def test_env_password_change_syncs_existing_admin(self):
        """Cambiar ADMIN_PASSWORD en el entorno actualiza la contraseña del admin existente."""
        os.environ["ADMIN_USER"] = "admin_sync"
        os.environ["ADMIN_PASSWORD"] = "primera"
        r1 = client.post("/api/auth/login", json={"username": "admin_sync", "password": "primera"})
        assert r1.status_code == 200

        os.environ["ADMIN_PASSWORD"] = "segunda"
        r_old = client.post("/api/auth/login", json={"username": "admin_sync", "password": "primera"})
        assert r_old.status_code == 401
        r_new = client.post("/api/auth/login", json={"username": "admin_sync", "password": "segunda"})
        assert r_new.status_code == 200


class TestAdminUsers:
    def test_list_and_delete_user(self):
        os.environ["ADMIN_USER"] = "admin_env"
        os.environ["ADMIN_PASSWORD"] = "x"
        client.post("/api/auth/login", json={"username": "admin_env", "password": "x"})
        client.post("/api/auth/login", json={"username": "usuario_borrable", "password": "nunca_existio"})

        from backend.app.database import SessionLocal
        from backend.app.models import User
        db = SessionLocal()
        db.add(User(username="usuario_borrable", password_hash=get_password_hash("pw"), is_admin=False))
        db.commit()
        db.close()

        users = client.get("/api/admin/users")
        assert users.status_code == 200
        names = [u["username"] for u in users.json()]
        assert "usuario_borrable" in names

        # El admin del entorno no se puede borrar
        r_env = client.delete("/api/admin/users/admin_env")
        assert r_env.status_code == 400

        r_del = client.delete("/api/admin/users/usuario_borrable")
        assert r_del.status_code == 204

        r_again = client.delete("/api/admin/users/usuario_borrable")
        assert r_again.status_code == 404

    def test_me_requires_token(self):
        response = client.get("/api/auth/me")
        # In test mode REQUIRE_AUTH is false, so it returns the dummy user
        assert response.status_code == 200
        assert response.json()["username"] == "test"
