# Training runs on a Kaggle GPU; everything else runs locally.
PY ?= .venv/bin/python
KAGGLE_USER ?= okbabouziane

kernel:   ; $(PY) kaggle/build_kernel.py --user $(KAGGLE_USER)
push:     ; kaggle kernels push -p build/kaggle-kernel
pull:     ; kaggle kernels output $(KAGGLE_USER)/invoicedesk-train -p build/kaggle-out
smoke:    ; $(PY) scripts/train.py --smoke --out build/smoke
baseline: ; $(PY) scripts/baseline_ocr.py --out build/local
report:   ; $(PY) scripts/report.py
test:     ; $(PY) -m pytest -q
lint:     ; .venv/bin/ruff check .
api:      ; MODEL_DIR=models/invoicedesk $(PY) -m uvicorn app.main:app --port 7860
web:      ; npm --prefix web run dev
web-check: ; npm --prefix web run lint && npm --prefix web run typecheck && npm --prefix web test && npm --prefix web run build

.PHONY: kernel push pull smoke baseline report test lint api web web-check
