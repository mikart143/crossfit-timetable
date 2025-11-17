#!/bin/bash
set -e

echo "🚀 Setting up development environment..."

# Ensure curl is available (AlmaLinux base image might be minimal)
if ! command -v curl >/dev/null 2>&1; then
  echo "🔧 Installing curl..."
  sudo dnf install -y curl
fi

# Install uv
echo "📦 Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh

# Make sure the installer-added path is available in this script
# uv currently installs into ~/.cargo/bin by default
export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

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