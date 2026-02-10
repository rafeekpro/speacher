# Branch Protection Rules Configuration

## How to set up branch protection for `main` branch

1. Go to your repository on GitHub: https://github.com/rafeekpro/speecher
2. Navigate to **Settings** → **Branches**
3. Click **Add rule** under "Branch protection rules"
4. Enter `main` as the branch name pattern

### Required settings:

☑️ **Require a pull request before merging**
- ☑️ Require approvals: 1
- ☑️ Dismiss stale pull request approvals when new commits are pushed
- ☑️ Require review from CODEOWNERS (optional)

☑️ **Require status checks to pass before merging**
- ☑️ Require branches to be up to date before merging
- **Required status checks:**
  - `🧪 Run All Tests`
  - `🐳 Docker Build Test`
  - `✅ PR Status Check`

☑️ **Require conversation resolution before merging**

☑️ **Require linear history** (optional - prevents merge commits)

☑️ **Include administrators** (optional - applies rules to admins too)

### Additional recommended settings:

☑️ **Automatically delete head branches** (in General settings)
- Cleans up branches after PR merge

## GitHub Actions Status Checks

The following checks will run automatically on every PR:

### Required (blocking):
1. **🧪 Run All Tests** - Must pass for merge
   - Unit tests with coverage
   - Integration tests
   - Test results posted as PR comment

2. **🐳 Docker Build Test** - Must pass for merge
   - Builds backend Docker image
   - Builds frontend Docker image
   - Validates docker-compose

### Informational (non-blocking):
3. **🎨 Code Quality** - Informational only
   - Black formatting check
   - isort import sorting
   - Flake8 linting
   - Pylint analysis

4. **🔒 Security Scan** - Informational only
   - Bandit security scan
   - Safety dependency check

5. **✅ PR Status Check** - Summary of all checks
   - Posts final status comment
   - Fails if required checks fail

## Testing the Setup

1. Create a new branch:
```bash
git checkout -b test/pr-checks
```

2. Make a small change:
```bash
echo "# Test" >> README.md
git add README.md
git commit -m "Test PR checks"
git push origin test/pr-checks
```

3. Create a PR on GitHub
4. Watch the checks run automatically
5. Verify you cannot merge until checks pass

## Bypass Protection (Emergency Only)

If you need to bypass protection in an emergency:
1. Go to Settings → Branches
2. Edit the rule for `main`
3. Temporarily disable or modify rules
4. **Remember to re-enable after emergency fix!**

## PR Check Commands

You can also run checks locally before creating a PR:

```bash
# Run all tests
./run_api_tests.sh

# Check formatting
black --check src/ tests/
isort --check-only src/ tests/

# Run linting
flake8 src/ tests/ --max-line-length=120

# Build Docker images
docker build -t speecher-backend:local .
docker build -t speecher-frontend:local ./src/frontend
```