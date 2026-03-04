import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.init_db import init_db
from backend.database.session import Base, engine

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db() # creates tables and FTS virtual table

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_get_metrics():
    response = client.get("/api/v1/metrics/ocr")
    assert response.status_code == 200
    data = response.json()
    assert "total_receipts_processed" in data
    assert "automation_rate" in data

def test_upload_invalid_file():
    from io import BytesIO
    files = {"file": ("test.txt", BytesIO(b"not an image"), "text/plain")}
    response = client.post("/api/v1/expenses/upload", files=files)
    assert response.status_code == 400
    assert "must be an image" in response.json()["detail"]

# To test actual OCR, we'd need a mock of the PyTesseract call.
# Skipping real image upload test in integration to avoid heavy OpenCV/Tesseract processing delays in CI.
