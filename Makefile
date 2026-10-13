.PHONY: help install lint format test run docker-build docker-run

# Colors
CYAN := \033[36m
GREEN := \033[32m
BLUE := \033[34m
BOLD := \033[1m
RESET := \033[0m

.DEFAULT_GOAL := help

help:
	@echo "\n$(BOLD)$(CYAN) Extração NF com LLM$(RESET)"
	@echo ""
	@echo "  ├── $(BOLD)$(GREEN)install$(RESET) ─ Install all dependencies with uv"
	@echo "  ├── $(BOLD)$(GREEN)lint$(RESET) ─ Run code quality checks (ruff + mypy)"
	@echo "  ├── $(BOLD)$(GREEN)format$(RESET) ─ Auto-format your code with ruff"
	@echo "  ├── $(BOLD)$(GREEN)test$(RESET) ─ Run tests with coverage report"
	@echo "  ├── $(BOLD)$(GREEN)run$(RESET) ─ Start development server (hot reload)"
	@echo "  ├── $(BOLD)$(GREEN)docker-build$(RESET) ─ Build the Docker image"
	@echo "  ├── $(BOLD)$(GREEN)docker-run$(RESET) ─ Run the Docker image using .env"
	@echo "  └── $(BOLD)$(GREEN)help$(RESET) ─ Show this beautiful help message"
	@echo ""
	@echo "  $(BOLD)$(BLUE)💡 Tip:$(RESET) Run $(CYAN)make install$(RESET) first if this is your first time!\n"

install:
	uv sync --all-extras

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run mypy src tests

format:
	uv run ruff check --fix src tests
	uv run ruff format src tests

test:
	uv run pytest --cov

run:
	uv run uvicorn extracao_nf.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker build -t extracao-nf-llm .

docker-run:
	docker run --rm -p 8000:8000 --env-file .env extracao-nf-llm
