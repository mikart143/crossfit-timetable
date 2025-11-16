#!/bin/bash
set -e

echo "🚀 Setting up development environment..."

# Install uv
echo "📦 Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/home/vscode/.cargo/bin:$PATH"

# Install Python dependencies
echo "📚 Installing project dependencies..."
uv sync --group dev

# Verify installation
echo "✅ Verifying installation..."
uv run python --version
uv run pytest --version
uv run ruff --version

echo "✨ Development environment ready!"
echo "💡 Run 'uv run uvicorn crossfit_timetable.main:app --reload' to start the FastAPI server"
