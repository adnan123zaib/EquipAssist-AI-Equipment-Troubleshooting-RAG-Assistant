import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402

EMAIL = "sample-evaluator@example.com"
PASSWORD = "SampleEval123!"


def authenticate(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Sample Evaluator",
            "email": EMAIL,
            "password": PASSWORD,
        },
    )
    if response.status_code == 409:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
        )
    response.raise_for_status()
    client.headers.update({"Authorization": f"Bearer {response.json()['access_token']}"})


with TestClient(app) as client:
    authenticate(client)
    manual = ROOT / "sample_data" / "PX-200_manual.pdf"
    with manual.open("rb") as f:
        response = client.post(
            "/api/v1/manuals/upload",
            files={"files": (manual.name, f, "application/pdf")},
            data={
                "equipment_name": "PX-200 Industrial Hydraulic Pump Controller",
                "manufacturer": "Northstar Industrial Controls",
                "model_number": "PX-200",
                "version": "1.4",
            },
        )
    print(response.status_code, response.json())
    response.raise_for_status()
