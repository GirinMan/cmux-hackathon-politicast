# PolitiKAST — developer Makefile
#
# Targets are intentionally thin wrappers so they're identical inside / outside
# Docker. Use `.venv/bin/python` so behavior matches the documented setup.

PY      ?= PYTHONPATH=. .venv/bin/python
PYTEST  ?= $(PY) -m pytest

.PHONY: help test test-fast schema-export migrate-dryrun migrate validate-scenarios lint clean ingest ingest-dryrun ingest-status resolve-pending llm-determinism db-up db-down db-reset db-logs migrate-db migrate-db-create migrate-duckdb-to-pg dev api-dev openapi-export mlflow-up mlflow-down init-mlflow-db calibrate-stage1 calibrate-stage2 build-tree retrodict

help:  ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-22s %s\n", $$1, $$2}'

test:  ## Run the full pytest suite (tests/ only — ignores stale ui/* tests)
	$(PYTEST) tests/

test-fast:  ## Run the fast subset (data + sim + eval + kg unit tests)
	$(PYTEST) tests/ -x --tb=short

schema-export:  ## Export Pydantic schemas → _workspace/contracts/jsonschema/
	$(PY) scripts/export_jsonschema.py

migrate-dryrun:  ## Dry-run snapshot v0 → v1 migration (no writes)
	$(PY) scripts/migrate_snapshots_v0_to_v1.py --dry-run

migrate:  ## Apply snapshot v0 → v1 migration in-place
	$(PY) scripts/migrate_snapshots_v0_to_v1.py

validate-scenarios:  ## Validate 5 region scenario seeds (strict; ElectionCalendar autofill)
	$(PY) scripts/validate_scenarios.py --strict

lint:  ## Best-effort lint (ruff if installed; otherwise no-op)
	@if .venv/bin/python -c "import ruff" 2>/dev/null; then \
		.venv/bin/python -m ruff check src tests scripts; \
	else \
		echo "ruff not installed — skipping lint"; \
	fi

ingest:  ## Run all enabled ingestion adapters (staging → target MERGE). Pass ARGS="--source X" to filter.
	$(PY) -m src.ingest.pipeline $(ARGS)

ingest-dryrun:  ## Run ingestion in dry-run mode (staging only, no target MERGE).
	$(PY) -m src.ingest.pipeline --dry-run $(ARGS)

ingest-status:  ## Show recent ingest_run rows (ordered by started_at DESC).
	$(PY) -m src.ingest.pipeline --status --limit 20

resolve-pending:  ## Re-run EntityResolver on unresolved_entity rows (status=pending).
	$(PY) -m src.ingest.resolver --apply-pending $(ARGS) || \
		echo "(resolve-pending CLI not implemented; run via Python: from src.ingest.resolver import EntityResolver)"

llm-determinism:  ## Run #55 gate — 2-run cache hit ≥ 0.9 + sha256 determinism.
	$(PYTEST) tests/ingest/test_llm_cache_determinism.py -v

api-dev:  ## Run FastAPI backend locally with uvicorn (reload).
	$(PY) -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

openapi-export:  ## Export OpenAPI 3.x JSON to _workspace/contracts/openapi.json (frontend codegen input).
	$(PY) scripts/export_openapi.py

# ---------------------------------------------------------------------------
# Phase 4 — Postgres + Neo4j (docker-compose)
# ---------------------------------------------------------------------------
db-up:  ## Start postgres + neo4j containers.
	docker compose up -d postgres neo4j

db-down:  ## Stop containers (keeps volumes).
	docker compose stop postgres neo4j

db-reset:  ## Destroy DB volumes (DANGEROUS) and recreate.
	docker compose down -v postgres neo4j || true
	docker compose up -d postgres neo4j

db-logs:  ## Tail logs of postgres + neo4j.
	docker compose logs -f postgres neo4j

migrate-db:  ## Run alembic upgrade head against POLITIKAST_PG_DSN.
	$(PY) -m alembic upgrade head

migrate-db-create:  ## Generate a new alembic revision (NAME=...).
	$(PY) -m alembic revision --autogenerate -m "$(NAME)"

migrate-duckdb-to-pg:  ## Migrate _workspace/db/politikast.duckdb → Postgres (idempotent).
	$(PY) tools/migrate_duckdb_to_postgres.py $(ARGS)

dev:  ## Bring up full dev stack (postgres + neo4j + backend + frontend) via docker compose.
	docker compose --profile ui up -d --build

# ---------------------------------------------------------------------------
# Phase 6 — MLflow tracking + scenario tree pipeline
# ---------------------------------------------------------------------------
mlflow-up:  ## Start mlflow tracking server (port 5000). Requires postgres up.
	docker compose up -d mlflow

mlflow-down:  ## Stop mlflow tracking server (keeps volume + DB).
	docker compose stop mlflow

init-mlflow-db:  ## Create the `mlflow` postgres DB (idempotent). Requires postgres running.
	bash tools/init_mlflow_db.sh

calibrate-stage1:  ## Stage 1 hyperparameter grid (Optuna) → MLflow. Override REGION=...
	$(PY) -m src.train.calibrate --stage 1 --regions $(or $(REGION),seoul_mayor)

calibrate-stage2:  ## Stage 2 prompt variant comparison (LLM-judge) → MLflow. Override REGION=...
	$(PY) -m src.train.calibrate --stage 2 --regions $(or $(REGION),seoul_mayor)

build-tree:  ## Build scenario tree. Args: REGION=... AS_OF=YYYY-MM-DD [BEAM_WIDTH=3 BEAM_DEPTH=4]
	$(PY) -m src.sim.scenario_tree \
		--region $(or $(REGION),seoul_mayor) \
		--as-of $(or $(AS_OF),2026-04-26) \
		--beam-width $(or $(BEAM_WIDTH),3) \
		--beam-depth $(or $(BEAM_DEPTH),4)

retrodict:  ## Past election validation harness. Args: REGION=... [WINDOW=train_2022]
	$(PY) -m src.eval.validation_harness \
		--region $(or $(REGION),seoul_mayor) \
		--window $(or $(WINDOW),train_2022)

clean:  ## Remove pyc / __pycache__
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.py[co]' -delete
