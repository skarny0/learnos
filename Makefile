# LearnOS — one-command onboarding.  `make` lists everything; most people only need:
#     make build    # one time: Python venv + both packages + .env
#     make start    # run LearnOS, open the desktop, play a demo episode on it
.DEFAULT_GOAL := help
SHELL := /bin/bash

VENV   := .venv
PY     := $(VENV)/bin/python
PORT   ?= 8000
URL    := http://localhost:$(PORT)
DELAY  ?= 1.5
# Run the env outside Docker against the repo's instances; data goes to ./data like the compose volume.
RUN_ENV := LEARNOS_INSTANCES_DIR=$(CURDIR)/instances LEARNOS_DATA_DIR=$(CURDIR)/data \
           LEARNOS_MODE=$${LEARNOS_MODE:-sim} LEARNOS_GRADER_TOKEN=$${LEARNOS_GRADER_TOKEN:-change-me}
OPEN := $(shell command -v open || command -v xdg-open || echo echo)

.PHONY: help build start serve demo notebook test validate ui up down logs doctor clean

help:  ## Show this list
	@echo "LearnOS — run 'make build' once, then 'make start'."
	@echo
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

build: $(VENV)/.installed .env  ## One-time setup: venv, env + client packages, Jupyter, .env
	@echo "✓ Built. Next: make start"

$(VENV)/.installed: env/pyproject.toml client/pyproject.toml
	@command -v python3.12 >/dev/null || command -v uv >/dev/null || \
	  { echo "Need Python 3.12 (brew install python@3.12) or uv (brew install uv)"; exit 1; }
	@if command -v uv >/dev/null; then \
	  { [ -x $(PY) ] || uv venv -q --python 3.12 $(VENV); } && \
	  uv pip install -q --python $(PY) -e "env[dev]" -e "client[pandas]" jupyterlab; \
	else \
	  { [ -x $(PY) ] || python3.12 -m venv $(VENV); } && $(PY) -m pip install -q --upgrade pip && \
	  $(PY) -m pip install -q -e "env[dev]" -e "client[pandas]" jupyterlab; \
	fi
	@touch $@

.env:
	@cp .env.example .env && echo "Created .env (add OPENAI_API_KEY / LANGFUSE_* keys there; it is gitignored)"

start: build  ## Run LearnOS, open the desktop, play a demo episode (Ctrl-C to stop)
	@if curl -sf $(URL)/health >/dev/null; then \
	  echo "LearnOS is already running on $(URL)"; $(OPEN) $(URL)/ >/dev/null; $(MAKE) -s demo; \
	else \
	  set -a; [ -f .env ] && . ./.env; set +a; \
	  $(RUN_ENV) $(PY) -m uvicorn learnos_env.server:app --port $(PORT) --log-level warning & pid=$$!; \
	  trap "kill $$pid 2>/dev/null" EXIT INT TERM; \
	  for i in $$(seq 50); do curl -sf $(URL)/health >/dev/null && break; sleep 0.2; done; \
	  echo; echo "  LearnOS desktop:  $(URL)/"; echo "  API docs:         $(URL)/docs"; echo; \
	  $(OPEN) $(URL)/ >/dev/null; sleep 2; \
	  $(PY) scripts/demo_episode.py --delay $(DELAY) --env $(URL); \
	  echo; echo "Demo done. Server still running — Ctrl-C to stop (or 'make demo' in another terminal to replay)."; \
	  wait $$pid; \
	fi

serve: build  ## Run LearnOS only (no demo, no browser)
	@set -a; [ -f .env ] && . ./.env; set +a; \
	echo "LearnOS on $(URL)/  (docs at $(URL)/docs)"; \
	$(RUN_ENV) $(PY) -m uvicorn learnos_env.server:app --port $(PORT) --log-level warning

demo:  ## Replay the 16-step scripted demo against a running server (DELAY=0.3 for fast)
	@curl -sf $(URL)/health >/dev/null || { echo "No server on $(URL) — run 'make start' or 'make serve' first"; exit 1; }
	@python3 scripts/demo_episode.py --delay $(DELAY) --env $(URL)

notebook: build  ## Open the workshop notebook in Jupyter Lab
	@set -a; [ -f .env ] && . ./.env; set +a; \
	$(VENV)/bin/jupyter lab notebooks/learnos_workshop.ipynb --ServerApp.root_dir=$(CURDIR)

test: build  ## Run env + client tests
	@cd env && ../$(PY) -m pytest -q
	@cd client && ../$(PY) -m pytest -q

validate: build  ## Check the simulated learner against the published effect sizes
	@LEARNOS_INSTANCES_DIR=$(CURDIR)/instances $(PY) -m learnos_env.sim.validate

ui:  ## Rebuild the desktop (needs Node) into env/learnos_env/ui_dist
	@scripts/build_ui.sh

up: .env  ## Docker alternative: env on :8000, desktop on :8080
	docker compose up -d --build
	@echo "Desktop: http://localhost:8080   API: http://localhost:8000/docs"

down:  ## Stop the Docker stack
	docker compose down

logs:  ## Follow Docker logs
	docker compose logs -f

doctor:  ## Check prerequisites and what's running
	@printf "python3.12  "; command -v python3.12 >/dev/null && echo ok || echo "missing (or use uv)"
	@printf "uv          "; command -v uv >/dev/null && echo ok || echo "not installed (optional)"
	@printf "docker      "; docker info >/dev/null 2>&1 && echo "running" || echo "not running (optional; only for 'make up')"
	@printf "node        "; command -v node >/dev/null && echo ok || echo "not installed (optional; only for 'make ui')"
	@printf "venv        "; [ -f $(VENV)/.installed ] && echo built || echo "not built — run 'make build'"
	@printf ".env        "; [ -f .env ] && echo present || echo "missing — 'make build' creates it"
	@printf "port $(PORT)   "; curl -sf $(URL)/health >/dev/null && echo "LearnOS running" || \
	  { lsof -ti :$(PORT) >/dev/null 2>&1 && echo "busy (something else)" || echo free; }

clean:  ## Remove the venv and local episode data (keeps .env)
	rm -rf $(VENV) data/traces/*.jsonl notebooks/learnos_data learnos_data
