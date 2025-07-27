.PHONY: install-dev format lint type-check check-all clean

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
