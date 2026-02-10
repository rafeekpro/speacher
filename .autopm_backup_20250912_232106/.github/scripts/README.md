# GitHub Workflow Validation System

A comprehensive validation system that prevents CI/CD failures by catching workflow errors before pushing to GitHub.

## Features

- **YAML Syntax Validation**: Checks for valid YAML structure and formatting
- **Command Validation**: Detects potentially missing commands on runners
- **Action Verification**: Validates action references and version tags
- **Environment Variable Checking**: Identifies undefined or missing variables
- **Job Dependency Validation**: Ensures job dependencies are correctly defined
- **Pre-push Hook Integration**: Automatically validates workflows before push
- **Customizable Configuration**: Adjust validation rules via JSON config

## Installation

### Quick Setup

Run the installation script to set up the pre-push hook:

```bash
./.githooks/install-hooks.sh
```

This will:
1. Install the pre-push hook
2. Configure Git to use the custom hooks directory
3. Enable automatic workflow validation before pushing

### Manual Setup

If you prefer manual configuration:

```bash
# Make scripts executable
chmod +x .github/scripts/validate-workflows.sh
chmod +x .githooks/pre-push

# Configure Git to use custom hooks
git config core.hooksPath .githooks
```

## Usage

### Automatic Validation (Pre-push Hook)

Once installed, the system automatically validates workflows when you push:

```bash
git push origin main
# Workflows are automatically validated
# Push is blocked if validation fails
```

To bypass validation (not recommended):
```bash
git push --no-verify
```

### Manual Validation

#### Validate All Workflows

```bash
./.github/scripts/validate-workflows.sh
```

#### Validate Specific Workflow

```bash
./.github/scripts/validate-workflows.sh .github/workflows/ci.yml
```

#### Validate Multiple Workflows

```bash
./.github/scripts/validate-workflows.sh .github/workflows/ci.yml .github/workflows/deploy.yml
```

## Configuration

Edit `.github/scripts/validation-config.json` to customize validation behavior:

```json
{
  "skip_cloud_tools": false,    // Skip validation of cloud CLI tools
  "strict_mode": false,          // Enable strict validation
  "ignored_workflows": [],       // List of workflows to skip
  "custom_checks": {
    "require_version_tags": true,
    "check_deprecated_actions": true,
    "validate_secrets": true,
    "check_environment_vars": true
  }
}
```

## Validation Checks

### 1. YAML Syntax
- Validates proper YAML structure
- Checks for tabs vs spaces
- Ensures proper indentation

### 2. Workflow Structure
- Verifies required fields (name, on, jobs)
- Checks for workflow triggers
- Validates job definitions

### 3. Commands
- Identifies potentially missing commands
- Warns about cloud CLI tools that might not be available
- Suggests alternatives for missing tools

### 4. Actions
- Checks for typos in action names
- Validates version tags
- Warns about deprecated actions

### 5. Environment Variables
- Identifies undefined environment variables
- Checks secret references
- Validates variable usage

### 6. Job Dependencies
- Ensures referenced jobs exist
- Validates dependency chains
- Checks for circular dependencies

## Common Issues and Solutions

### Missing Cloud CLI Tools

**Problem**: Commands like `aws`, `az`, or `gcloud` fail on runners

**Solution**: Make commands optional with `|| true`:
```yaml
- name: Test Cloud CLIs (Optional)
  run: |
    aws --version || echo "AWS CLI not installed"
    az --version || echo "Azure CLI not installed"
```

### YAML Syntax Errors

**Problem**: Invalid YAML structure

**Solution**: 
- Use spaces, not tabs
- Check indentation (2 spaces per level)
- Quote strings with special characters
- Validate with online YAML validators

### Deprecated Actions

**Problem**: Using old versions of GitHub Actions

**Solution**: Update to latest versions:
```yaml
# Old
- uses: actions/checkout@v2

# New
- uses: actions/checkout@v4
```

### Missing Environment Variables

**Problem**: Using undefined environment variables

**Solution**: Define variables at workflow, job, or step level:
```yaml
env:
  MY_VAR: value

jobs:
  build:
    env:
      JOB_VAR: value
    steps:
      - name: Step
        env:
          STEP_VAR: value
```

## Output Examples

### Successful Validation

```
✅ All workflows validated successfully!

  Total workflows: 5
  Passed: 5
  Failed: 0
  Warnings: 0
```

### Validation with Warnings

```
⚠️ Validation passed with warnings. Review them before pushing.

  Total workflows: 3
  Passed: 3
  Failed: 0
  Warnings: 4

Warnings:
  • test.yml: Cloud CLI 'aws' might not be available on runners
  • deploy.yml: Using deprecated checkout version (upgrade to v4)
```

### Failed Validation

```
❌ Validation failed! Fix errors before pushing.

  Total workflows: 2
  Passed: 1
  Failed: 1
  Warnings: 2

Errors found:
  • broken.yml: Invalid YAML syntax
  • broken.yml: Missing 'jobs' definition
```

## Uninstallation

To remove the validation system:

```bash
# Remove Git hooks configuration
git config --unset core.hooksPath

# Or restore default hooks
git config core.hooksPath .git/hooks
```

## Dependencies

### Required
- Bash 4.0+
- Git

### Optional (Recommended)
- `yq` - Advanced YAML parsing
- Python with PyYAML - YAML validation
- `shellcheck` - Shell script validation

### Installation of Optional Dependencies

```bash
# macOS
brew install yq python
pip3 install pyyaml

# Ubuntu/Debian
sudo apt-get install yq python3-yaml

# Using pip
pip install yq pyyaml
```

## Contributing

To improve the validation system:

1. Edit validation rules in `validate-workflows.sh`
2. Update configuration schema in `validation-config.json`
3. Add new checks as functions
4. Test with sample workflows
5. Update this documentation

## License

This validation system is part of the project and follows the same license.