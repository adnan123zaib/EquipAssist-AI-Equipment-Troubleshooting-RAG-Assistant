import atexit
import os
import shutil
import tempfile
from pathlib import Path


# Create a completely separate database and vector index for every test run.
TEST_ROOT = Path(tempfile.mkdtemp(prefix="equipment-rag-tests-"))

# Remove temporary test files after pytest finishes.
atexit.register(
    shutil.rmtree,
    TEST_ROOT,
    ignore_errors=True,
)

os.environ.update(
    {
        "APP_ENV": "test",
        "DATABASE_URL": (
            f"sqlite:///{(TEST_ROOT / 'test_equipment.db').as_posix()}"
        ),
        "LLM_PROVIDER": "local",
        "EMBEDDING_PROVIDER": "local",
        "CHROMA_PERSIST_DIRECTORY": str(TEST_ROOT / "chroma"),
        "JWT_SECRET_KEY": "test-only-secret",
        "APP_ENCRYPTION_KEY": "5W6l7rG8h9iJ0kL1mN2oP3qR4sT5uV6wX7yZ8aB9cD0=",
        "MANUAL_STORAGE_DIRECTORY": str(TEST_ROOT / "manuals"),
        "SIMILARITY_THRESHOLD": "0.20",
        "CHUNK_SIZE": "500",
        "CHUNK_OVERLAP": "80",
    }
)

# These imports must remain below os.environ.update().
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Test Engineer",
                "email": "engineer@example.com",
                "password": "StrongPass123!",
            },
        )

        if response.status_code == 409:
            response = test_client.post(
                "/api/v1/auth/login",
                json={
                    "email": "engineer@example.com",
                    "password": "StrongPass123!",
                },
            )

        assert response.status_code in (200, 201), response.text

        test_client.headers.update(
            {
                "Authorization": (
                    f"Bearer {response.json()['access_token']}"
                )
            }
        )

        yield test_client


@pytest.fixture(scope="session")
def sample_pdf():
    return (
        Path(__file__).resolve().parents[2]
        / "sample_data"
        / "PX-200_manual.pdf"
    )