"""API for the web app: upload an invoice photo, get its fields and arithmetic checks, ask questions.

Nothing is stored: every request carries the image, and the chat history lives only in the
browser tab (it is gone after a refresh).

  MODEL_DIR=models/invoicedesk uvicorn app.main:app --port 7860

In production the same process serves the built React app (web/dist, see the Dockerfile); in
development Vite serves it and proxies /api and /samples here.
"""

from __future__ import annotations

import io
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Protocol

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from invoicedesk.normalize import checks, parse_amount, parse_date, tidy

SAMPLES = Path(__file__).parent / "samples"
WEB_DIST = Path(os.environ.get("WEB_DIST", Path(__file__).parents[1] / "web" / "dist"))
MAX_BYTES = 6 * 1024 * 1024
MAX_QUESTION = 200
MAX_PIXELS = 30_000_000


class Reader(Protocol):
    def extract(self, image: Image.Image) -> dict[str, Any]: ...
    def ask(self, image: Image.Image, question: str) -> str: ...


class RateLimiter:
    """Sliding window per client: at most `limit` requests in `window` seconds (in memory, one process)."""

    def __init__(self, limit: int, window: float, clock=time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self.hits: dict[str, deque] = defaultdict(deque)

    def retry_after(self, key: str) -> int:
        now = self.clock()
        q = self.hits[key]
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return max(1, int(self.window - (now - q[0])) + 1)
        q.append(now)
        return 0


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


async def read_upload(upload: UploadFile) -> tuple[Image.Image, bytes, str]:
    """The decoded image, its bytes and its media type; rejects anything but a JPEG or PNG."""
    data = await upload.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "The image must be at most 6 MB.")
    try:
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        img = Image.open(io.BytesIO(data))
        fmt = img.format
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as err:
        raise HTTPException(422, "Upload a JPEG or PNG image of an invoice.") from err
    if fmt not in ("JPEG", "PNG"):
        raise HTTPException(422, "Upload a JPEG or PNG image of an invoice.")
    return img.convert("RGB"), data, f"image/{fmt.lower()}"


async def read_image(upload: UploadFile) -> Image.Image:
    return (await read_upload(upload))[0]


def typed(fields: dict[str, Any]) -> dict[str, Any]:
    """The values an accounting system needs as numbers and dates."""
    out: dict[str, Any] = {k: parse_amount(fields.get(k)) for k in ("total_ht", "tva", "timbre", "total_ttc")}
    out["date"] = parse_date(fields.get("date"))
    return {k: v for k, v in out.items() if v is not None}


def create_app(reader: Reader, model_name: str = "", limiter: RateLimiter | None = None) -> FastAPI:
    api = FastAPI(title="InvoiceDesk", docs_url=None, redoc_url=None)
    limiter = limiter or RateLimiter(int(os.environ.get("RATE_LIMIT_PER_MINUTE", "20")), 60)

    def guard(request: Request) -> None:
        wait = limiter.retry_after(client_key(request))
        if wait:
            raise HTTPException(429, f"Too many requests. Try again in {wait} seconds.",
                                headers={"Retry-After": str(wait)})

    def check_question(question: str) -> str:
        question = question.strip()
        if not question:
            raise HTTPException(422, "Type a question.")
        if len(question) > MAX_QUESTION:
            raise HTTPException(422, f"Questions are limited to {MAX_QUESTION} characters.")
        return question

    def read_fields(img: Image.Image) -> dict[str, Any]:
        t0 = time.perf_counter()
        fields = tidy(reader.extract(img))
        return {"model": model_name, "fields": fields, "typed": typed(fields), "checks": checks(fields),
                "seconds": round(time.perf_counter() - t0, 2)}

    def answer(img: Image.Image, question: str) -> dict[str, Any]:
        t0 = time.perf_counter()
        text = reader.ask(img, question)
        return {"model": model_name, "question": question, "answer": text,
                "seconds": round(time.perf_counter() - t0, 2)}

    @api.get("/health")
    def health():
        return {"ok": True, "model": model_name}

    @api.post("/api/extract")
    async def extract(request: Request, image: UploadFile = File(...)):
        guard(request)
        return read_fields(await read_image(image))

    @api.post("/api/ask")
    async def ask(request: Request, image: UploadFile = File(...), question: str = Form(...)):
        guard(request)
        question = check_question(question)
        return answer(await read_image(image), question)

    api.mount("/samples", StaticFiles(directory=SAMPLES), name="samples")
    if WEB_DIST.is_dir():  # built front end; mounted last so /api routes win
        api.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
    return api


def _default_app() -> FastAPI:
    import torch

    from invoicedesk.reader import DonutReader

    torch.set_num_threads(int(os.environ.get("TORCH_THREADS", "4")))
    model_dir = os.environ.get("MODEL_DIR", "models/invoicedesk")
    return create_app(DonutReader(model_dir), Path(model_dir).name)


app = _default_app() if os.environ.get("INVOICEDESK_NO_AUTOLOAD") != "1" else None
