"""Pytest configuration and shared fixtures."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import Role, User

# ── In-memory SQLite for tests (overrides PostgreSQL) ────────────────────────
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Create all tables once per test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Return a test DB session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


def _create_user(db, email: str, password: str, role: Role) -> User:
    """Helper to create a user in the test DB."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=f"Test {role}",
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@pytest.fixture(scope="session")
def admin_user(db=None):
    session = TestingSessionLocal()
    user = _create_user(session, "admin@test.dev", "Admin@123", Role.ADMIN)
    session.close()
    return user


@pytest.fixture(scope="session")
def viewer_user(db=None):
    session = TestingSessionLocal()
    user = _create_user(session, "viewer@test.dev", "Viewer@123", Role.VIEWER)
    session.close()
    return user


def _get_token(client, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]
