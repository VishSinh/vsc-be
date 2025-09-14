.PHONY: install-dev format lint type-check check-all clean docker-down docker-down-v docker-prune docker-reset docker-build docker-up

# Install development dependencies
install-dev:
	pipenv install --dev

# Format code with black and isort
format:
	pipenv run black . --exclude "migrations|scripts"
	pipenv run isort . --skip "migrations,scripts"

# Lint code with flake8
lint:
	pipenv run flake8 . --exclude migrations,scripts

# Type checking with mypy
type-check:
	pipenv run mypy . --config-file=mypy.ini

# Run all checks
check-all: format lint type-check

# Clean up cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

# Install pre-commit hooks
install-hooks:
	pipenv run pre-commit install

# Run pre-commit on all files
pre-commit-all:
	pipenv run pre-commit run --all-files

docker-down:
	docker compose down --remove-orphans

docker-down-v:
	docker compose down -v --remove-orphans

docker-prune:
	docker system prune -af --volumes

docker-reset:
	docker compose down -v --remove-orphans && docker system prune -af --volumes

docker-build:
	docker compose build

docker-up:
	docker compose up -d --build
