# Pyramid Project - CI/CD Pipeline

This directory contains GitHub Actions workflows for the Pyramid project within the mono repository.

## Workflows

### `pyramid-ci.yml` - Continuous Integration Pipeline

Automatically runs on pull requests and pushes to main that affect the `Pyramid/` directory.

**Pipeline Stages:**

1. **Lint Check** (Job 1)

   - Python syntax validation using Flake8
   - Code quality checks using Pylint
   - Excludes migrations and cache files

2. **Unit Tests** (Job 2) - Runs after lint passes

   - Django database migrations
   - Fixture data loading
   - Executes all unit tests
   - Optional coverage reporting

3. **Build & Dependency Check** (Job 3) - Runs after tests pass
   - Dependency installation and validation
   - Static file collection
   - Django configuration check
   - Application startup verification

## Branch Protection

To enforce PR-based workflow with required CI checks, follow the setup guide:

**→ See [BRANCH_PROTECTION_SETUP.md](./BRANCH_PROTECTION_SETUP.md) for detailed instructions**

## Local Development

Before pushing changes, run these checks locally:

```bash
cd Pyramid

# 1. Run linting
flake8 . --exclude=*/migrations/*,__pycache__,*.pyc,.venv,venv
pylint --disable=all --enable=E,F --ignore=migrations,__pycache__ kanoodleApp/ polysphere/

# 2. Run tests
python manage.py test

# 3. Check dependencies
pip check

# 4. Collect static files
python manage.py collectstatic --noinput
```

## Mono Repository Structure

This workflow is isolated to the Pyramid project:

- Uses path filters: `Pyramid/**`
- Sets working directory: `Pyramid/`
- Won't trigger for changes in other projects

## Status Badges

Add this badge to your README to show CI status:

```markdown
![Pyramid CI](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/pyramid-ci.yml/badge.svg)
```

Replace `YOUR_USERNAME` and `YOUR_REPO` with your actual GitHub repository details.
