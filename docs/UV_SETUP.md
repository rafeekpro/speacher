# 🚀 Using Speecher with UV Package Manager

UV is a blazingly fast Python package manager written in Rust. It's 10-100x faster than pip and provides better dependency resolution.

## 📦 Installation

### Install UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# or with Homebrew
brew install uv

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 🎯 Quick Start with UV

### 1. Create Virtual Environment

```bash
# Create a new virtual environment
uv venv

# Activate it
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies

```bash
# Install all dependencies
uv pip install -e .

# Or sync from pyproject.toml
uv pip sync pyproject.toml

# Install with dev dependencies
uv pip install -e ".[dev]"

# Install with test dependencies
uv pip install -e ".[test]"
```

### 3. Run the Application

#### Option A: Run Backend API
```bash
# Start the FastAPI backend
uv run python -m src.backend.main

# Or with uvicorn directly
uv run uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### Option B: Run Frontend UI
```bash
# Start Streamlit frontend
uv run streamlit run src/frontend/app.py

# Or specific page
uv run streamlit run src/frontend/pages/3_🎙️_Simple_Recording.py
```

#### Option C: Run CLI
```bash
# Use the CLI tool
uv run python -m src.speecher.cli --audio-file audio.wav --language pl-PL
```

#### Option D: Run Everything with Docker + UV
```bash
# Install dependencies locally with uv
uv pip install -e .

# Then run with docker compose (uses installed packages)
docker compose up
```

## 🧪 Development with UV

### Run Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_api.py

# Run integration tests
uv run pytest tests/test_integration.py -v
```

### Code Quality
```bash
# Format code with black
uv run black src/ tests/

# Sort imports
uv run isort src/ tests/

# Lint with ruff (faster than flake8)
uv run ruff check src/ tests/

# Type checking
uv run mypy src/
```

### Development Workflow
```bash
# Install in editable mode with all dev tools
uv pip install -e ".[dev]"

# Run formatters and linters
uv run black . && uv run isort . && uv run ruff check .

# Run tests before commit
uv run pytest --cov=src

# Start development servers
# Terminal 1: Backend
uv run uvicorn src.backend.main:app --reload

# Terminal 2: Frontend
uv run streamlit run src/frontend/app.py
```

## 🐳 Docker with UV

Create a Dockerfile optimized for UV:

```dockerfile
FROM python:3.11-slim

# Install UV
RUN pip install uv

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY src/ ./src/

# Install dependencies with UV (much faster than pip)
RUN uv pip install --system .

# Run the application
CMD ["python", "-m", "src.backend.main"]
```

## 📊 UV vs Other Package Managers

| Operation | UV | pip | poetry |
|-----------|-----|-----|--------|
| Install 50 packages | ~1s | ~10s | ~30s |
| Resolve dependencies | ~0.5s | ~5s | ~15s |
| Create venv | ~0.1s | ~2s | ~3s |

## 🎨 VS Code Integration

Add to `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black"
}
```

## 🔧 Troubleshooting

### Issue: UV not found
```bash
# Add to PATH
export PATH="$HOME/.cargo/bin:$PATH"
```

### Issue: Dependencies conflict
```bash
# Clear cache and reinstall
uv cache clean
uv pip install -e . --force-reinstall
```

### Issue: MongoDB connection error
```bash
# Make sure MongoDB is running
docker run -d -p 27017:27017 mongo:6.0
```

## 📚 Useful UV Commands

```bash
# Show installed packages
uv pip list

# Show package info
uv pip show fastapi

# Upgrade package
uv pip install --upgrade fastapi

# Install from requirements.txt
uv pip install -r requirements.txt

# Export dependencies
uv pip freeze > requirements.txt

# Create lock file
uv pip compile pyproject.toml -o requirements.lock

# Install from lock file
uv pip sync requirements.lock
```

## 🚀 One-liner Setup

```bash
# Complete setup in one command
curl -LsSf https://astral.sh/uv/install.sh | sh && \
  uv venv && \
  source .venv/bin/activate && \
  uv pip install -e ".[dev]" && \
  echo "✅ Ready! Run: uv run python -m src.backend.main"
```

## 🔗 Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [UV vs pip Benchmarks](https://github.com/astral-sh/uv#benchmarks)
- [Python Packaging Guide](https://packaging.python.org/)