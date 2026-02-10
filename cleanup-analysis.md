# Cleanup Analysis Report

## Project Structure Overview

The project appears to be a full-stack application with:

- React frontend (in `src/react-frontend/`)
- Python backend (in `src/backend/`)
- Python speecher module (in `src/speecher/`)
- Docker configurations at root level

## Files to Remove

### 1. Example Files (LOW RISK - Safe to remove)

**Location:** `src/react-frontend/src/`

- `App.auth.example.tsx` - Example authentication implementation
- `App.layout.example.tsx` - Example layout implementation

**Reason:** These are example/reference files that are no longer needed as the actual implementation exists in `App.tsx`

### 2. Coverage HTML Files (LOW RISK - Safe to remove)

**Location:** `src/react-frontend/coverage/lcov-report/src/`

- `App.auth.example.tsx.html`
- `App.layout.example.tsx.html`

**Reason:** Coverage reports for example files that shouldn't be tracked

### 3. Empty/Unused Directories (LOW RISK - Safe to remove)

- `test_results/` - Empty directory at project root
- `.coverage` file in react-frontend (if not needed for current testing)

### 4. Python Cache (LOW RISK - Safe to remove)

- `__pycache__` directories throughout the project
- `.pytest_cache` at project root

**Reason:** Cache files that are regenerated automatically

## Files to Keep

### Essential Configuration Files

- All `docker-compose*.yml` files (they serve different purposes)
- `requirements/` directory with modular requirements
- `.dockerignore`
- All test files (`*.test.tsx`, `*.test.ts`)
- All source code in `src/`

## Docker Compose Naming Recommendation

Current structure:

- `docker-compose.yml` - Simple MongoDB + backend setup
- `docker-compose.dev.yml` - Full development setup with PostgreSQL and MongoDB
- `docker-compose.prod.yml` - Production configuration

**Recommendation:** Keep current naming as it follows standard conventions:

- `docker-compose.yml` as the base/default
- `docker-compose.dev.yml` for development overrides
- `docker-compose.prod.yml` for production overrides

## No Old Frontend Found

- No old Flask or Streamlit frontend directories found
- The `src/speecher/` directory contains Python backend modules, not old frontend code

## Requirements Structure

The modular requirements structure in `requirements/` is well-organized:

- `base.txt` - Core dependencies
- `dev.txt` - Development tools
- `test.txt` - Testing dependencies
- `azure.txt` - Azure-specific dependencies

**Recommendation:** Keep this structure as-is
