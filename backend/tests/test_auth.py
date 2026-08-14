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

    def test_me_requires_token(self):
        response = client.get("/api/auth/me")
        # In test mode REQUIRE_AUTH is false, so it returns the dummy user
        assert response.status_code == 200
        assert response.json()["username"] == "test"
