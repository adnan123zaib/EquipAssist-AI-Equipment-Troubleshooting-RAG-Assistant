.PHONY: install test run build sample eval docker
install:
	pip install -r backend/requirements.txt
	cd frontend && npm install
test:
	cd backend && PYTHONPATH=. pytest -q
run:
	cd backend && PYTHONPATH=. uvicorn app.main:app --reload
build:
	cd frontend && npm run build
sample:
	PYTHONPATH=backend python scripts/ingest_sample_manual.py
eval:
	PYTHONPATH=backend python scripts/evaluate_sample_questions.py
docker:
	docker compose up --build

