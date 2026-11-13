import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

os.environ["INVOICEDESK_NO_AUTOLOAD"] = "1"
from app.main import RateLimiter, create_app  # noqa: E402


class FakeReader:
    def __init__(self):
        self.questions = []

    def extract(self, image):
        return {"total_ht": "1 000,00", "tva_rate": "19%", "tva": "190,00", "total_ttc": "1 190,00",
                "date": "26 janvier 2024", "items": [{"name": "A", "qty": "1", "unit_price": "1 000,00",
                                                      "amount": "1 000,00"}]}

    def ask(self, image, question):
        self.questions.append(question)
        return "1 190,00"


def jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 60), "white").save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def client():
    return TestClient(create_app(FakeReader(), "fake"))


def test_extract_returns_fields_typed_values_and_checks(client):
    r = client.post("/api/extract", files={"image": ("f.jpg", jpeg(), "image/jpeg")})
    assert r.status_code == 200
    body = r.json()
    assert body["typed"] == {"total_ht": 1000.0, "tva": 190.0, "total_ttc": 1190.0, "date": "2024-01-26"}
    assert all(c["ok"] for c in body["checks"])


def test_ask_answers_and_trims_the_question(client):
    r = client.post("/api/ask", files={"image": ("f.jpg", jpeg(), "image/jpeg")}, data={"question": "  Total TTC ? "})
    assert r.status_code == 200 and r.json()["answer"] == "1 190,00" and r.json()["question"] == "Total TTC ?"


def test_rejects_non_images_and_empty_questions(client):
    assert client.post("/api/extract", files={"image": ("f.txt", b"hello", "text/plain")}).status_code == 422
    r = client.post("/api/ask", files={"image": ("f.jpg", jpeg(), "image/jpeg")}, data={"question": " "})
    assert r.status_code == 422


def test_rejects_oversized_uploads(client):
    big = b"\xff" * (6 * 1024 * 1024 + 10)
    assert client.post("/api/extract", files={"image": ("f.jpg", big, "image/jpeg")}).status_code == 413


def test_rate_limit_per_client():
    c = TestClient(create_app(FakeReader(), "fake", RateLimiter(2, 60)))
    codes = [c.post("/api/extract", files={"image": ("f.jpg", jpeg(), "image/jpeg")}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_samples_and_health(client):
    assert client.get("/samples/sample-1.jpg").headers["content-type"] == "image/jpeg"
    assert client.get("/health").json() == {"ok": True, "model": "fake"}
