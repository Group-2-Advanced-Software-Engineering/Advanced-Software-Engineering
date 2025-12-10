# Branch Protection Setup Guide

This guide explains how to set up branch protection rules for the Pyramid project in your mono repository to enforce PR-based workflow with automated CI checks.

## Automated CI Workflow

The GitHub Actions workflow (`pyramid-ci.yml`) automatically runs on:

- **Pull Requests** targeting the `main` branch that modify files in the `Pyramid/` directory
- **Direct pushes** to `main` (for validation, but direct pushes should be blocked via branch protection)

### Workflow Stages

1. **Lint Check**
   - Runs Flake8 for Python syntax errors and code quality
   - Runs Pylint for additional error detection
2. **Unit Tests** (runs after lint passes)
   - Executes Django migrations
   - Loads fixture data
   - Runs all unit tests in `kanoodleApp.tests`
   - Optionally generates coverage report
3. **Build & Dependency Check** (runs after tests pass)
   - Installs all dependencies from `requirements.txt`
   - Validates dependency compatibility
   - Collects Django static files
   - Verifies application can start successfully

## Setting Up Branch Protection Rules

Follow these steps to enforce PR-based workflow and require passing CI checks:

**Note for Free Organization Plan:**

- ✅ Works for both public and private repos
- ⚠️ Required approvals only available for public repos or paid plans
- ✅ Status checks (CI pipeline) work on all plans

### Step 1: Navigate to Repository Settings

1. Go to your GitHub repository
2. Click on **Settings** (top navigation)
3. In the left sidebar, click on **Branches** (under "Code and automation")

### Step 2: Add Branch Protection Rule

1. Click **Add branch protection rule**
2. In "Branch name pattern", enter: `main`

### Step 3: Configure Protection Settings

Enable the following settings:

#### ✅ Require a pull request before merging

- **Check this box** to prevent direct pushes to main
- Configure sub-options:
  - ☑️ **Require approvals**: Set to at least 1 reviewer (recommended)
    - ⚠️ **Note**: This option is only available for:
      - Public repositories (any plan)
      - Private repositories on **paid plans** (Team, Enterprise)
    - ❌ **NOT available** for private repos on GitHub Free Organization plan
  - ☑️ **Dismiss stale pull request approvals when new commits are pushed** (if available)
  - ☑️ **Require review from Code Owners** (optional, if you have CODEOWNERS file, if available)

#### ✅ Require status checks to pass before merging

- **Check this box** to require CI checks to pass
- Click **Add check** and search for/add:
  - `Lint Check` (lint job from workflow)
  - `Unit Tests` (test job from workflow)
  - `Build & Dependency Check` (build job from workflow)
- ☑️ **Require branches to be up to date before merging** (recommended)

#### ✅ Require conversation resolution before merging (optional but recommended)

- Ensures all PR comments are addressed before merging

#### ✅ Do not allow bypassing the above settings (recommended)

- Prevents administrators from bypassing the rules
- Uncheck if you want admins to have override capability

#### ⚠️ Additional Recommended Settings:

- ☑️ **Require linear history** - Prevents merge commits, enforces rebase or squash
- ☑️ **Require deployments to succeed** - If you have deployment workflows
- ☑️ **Lock branch** - Prevents any modifications (use only for archived branches)

### Step 4: Save Changes

1. Scroll to the bottom
2. Click **Create** or **Save changes**

## Workflow

Once configured, the development workflow will be:

### For Free Organization Plan (Private Repo):

1. **Developer creates a feature branch**

   ```bash
   git checkout -b feature/my-feature
   ```

2. **Developer makes changes and commits**

   ```bash
   git add Pyramid/
   git commit -m "Add new feature"
   git push origin feature/my-feature
   ```

3. **Developer creates a Pull Request**

   - Go to GitHub repository
   - Click "Pull requests" → "New pull request"
   - Select base: `main` and compare: `feature/my-feature`
   - Click "Create pull request"

4. **CI Pipeline automatically triggers**

   - GitHub Actions runs the `pyramid-ci.yml` workflow
   - All three jobs (lint, test, build) must pass
   - Status checks appear on the PR page

5. **Merge** (after CI passes)
   - **Free plan**: Developer can merge once CI passes (no approval required)
   - **Paid plan/Public repo**: Reviewer(s) must approve first, then merge
   - Choose merge strategy (Merge commit, Squash and merge, or Rebase and merge)

### For Public Repositories or Paid Plans:

Same workflow as above, but step 5 includes:

- Required reviewer approvals (configurable number)
- All conversation threads must be resolved (if enabled)
- Then merge is allowed

## Blocking Direct Pushes

With branch protection enabled, direct pushes to `main` will be blocked:

```bash
git push origin main
# Error: Changes must be made through a pull request.
```

## Mono Repository Considerations

The workflow is specifically configured for the Pyramid project:

- **Path filters**: Only triggers when files in `Pyramid/` directory are changed
- **Working directory**: All jobs run with `working-directory: Pyramid`
- **Independent**: Won't interfere with other projects in your mono repo

If you add other projects, create separate workflow files (e.g., `project2-ci.yml`) with appropriate path filters.

## Testing the Setup

To verify everything works:

1. Create a test branch:

   ```bash
   git checkout -b test/ci-setup
   ```

2. Make a small change in the Pyramid directory:

   ```bash
   echo "# Test" >> Pyramid/README
   git add Pyramid/README
   git commit -m "Test CI setup"
   git push origin test/ci-setup
   ```

3. Create a PR on GitHub
4. Verify that the workflow runs automatically
5. Check that all three jobs complete successfully

## Troubleshooting

### CI Fails on Lint

- Check Flake8 errors in the workflow logs
- Fix code style issues locally before pushing

### CI Fails on Tests

- Ensure all tests pass locally: `python manage.py test`
- Check if fixture files are properly committed

### CI Fails on Build

- Verify `requirements.txt` is up to date
- Test locally: `pip install -r requirements.txt`

### Status Checks Don't Appear

- Ensure workflow file is in `.github/workflows/`
- Verify branch protection is set up correctly
- Check that path filters match your changes

## Additional Resources

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Django Testing Documentation](https://docs.djangoproject.com/en/stable/topics/testing/)
