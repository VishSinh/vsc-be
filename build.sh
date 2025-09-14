#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pipenv install

# Convert static asset files
pipenv run python manage.py collectstatic --no-input

# Apply any outstanding database migrations
pipenv run python manage.py migrate
