#!/bin/bash
# Local CI checks script - Run this before pushing to GitHub
# This mimics the GitHub Actions CI workflow

set -e  # Exit on first error

echo "🔍 Running CI checks locally..."
echo ""

# Change to Pyramid directory
cd "$(dirname "$0")"

echo "========================================="
echo "📋 Step 1: Linting with Flake8"
echo "========================================="

# Check for critical syntax errors (will fail if errors found)
echo "Checking for Python syntax errors and undefined names..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics \
  --exclude='*/migrations/*,__pycache__,*.pyc,.venv,venv' || {
  echo "❌ Critical syntax errors found! Please fix them before pushing."
  exit 1
}
echo "✅ No critical syntax errors found"
echo ""

# Check for code style issues (warnings only, won't fail)
echo "Checking code style (warnings only)..."
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics \
  --exclude='*/migrations/*,__pycache__,*.pyc,.venv,venv'
echo ""

echo "========================================="
echo "🧪 Step 2: Running Unit Tests"
echo "========================================="

# Run Django migrations
echo "Running Django migrations..."
python manage.py migrate --noinput || {
  echo "❌ Migration failed!"
  exit 1
}
echo "✅ Migrations completed"
echo ""

# Load fixture data
echo "Loading fixture data..."
python manage.py loaddata kanoodleApp/JSONs/piece_data.json 2>/dev/null || true
python manage.py loaddata kanoodleApp/JSONs/pyramid_piece_data.json 2>/dev/null || true
echo ""

# Run tests
echo "Running unit tests..."
python manage.py test kanoodleApp.tests --verbosity=2 || {
  echo "❌ Tests failed!"
  exit 1
}
echo "✅ All tests passed"
echo ""

echo "========================================="
echo "🏗️  Step 3: Build & Dependency Check"
echo "========================================="

# Check dependencies
echo "Checking for missing dependencies..."
python -m pip check || {
  echo "❌ Dependency check failed!"
  exit 1
}
echo "✅ All dependencies OK"
echo ""

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput || {
  echo "❌ Static file collection failed!"
  exit 1
}
echo "✅ Static files collected"
echo ""

echo "========================================="
echo "✅ All CI checks passed!"
echo "========================================="
echo ""
echo "You can now safely push your changes to GitHub."
echo "The CI workflow will run the same checks on GitHub Actions."
