# Dev Container Configuration

This directory contains the configuration for the VS Code Dev Container for the CrossFit Timetable project.

## What's Included

### Base Image
- AlmaLinux 9
- Git and common development tools

### VS Code Extensions
- **Python Support**: Python extension, Pylance, debugpy
- **Linting & Formatting**: Ruff
- **Configuration Files**: Even Better TOML, YAML
- **Development**: GitHub Copilot, REST Client

### Python Environment
- **uv**: Fast Python package installer and resolver
- **Project Dependencies**: Installed automatically via `uv sync`
- **Dev Dependencies**: pytest, pytest-asyncio, ruff

### Port Forwarding
- Port 8000 (FastAPI server) is automatically forwarded

## Getting Started

1. Open the project in VS Code
2. When prompted, click "Reopen in Container" or run the command "Dev Containers: Reopen in Container"
3. Wait for the container to build and setup to complete
4. Start developing!

## Running the Application

```bash
# Start the FastAPI server
uv run uvicorn crossfit_timetable.main:app --reload

# Run tests
uv run pytest

# Run linting
uv run ruff check

# Format code
uv run ruff format
```

## Environment Variables

To set your own auth token, create a `.env` file in your local workspace or set it in your shell:

```bash
export APP_AUTH_TOKEN="your-secure-token"
```

## Customization

You can customize the dev container by editing:
- `.devcontainer/devcontainer.json` - Main configuration
- `.devcontainer/setup.sh` - Post-creation setup script

## Troubleshooting

### Container Build Fails
Try rebuilding the container: Command Palette → "Dev Containers: Rebuild Container"

### Python Not Found
The container uses a virtual environment at `.venv`. Make sure VS Code is using the correct interpreter: `${workspaceFolder}/.venv/bin/python`

### Port Already in Use
If port 8000 is already in use, you can change it in the `uvicorn` command or configure a different port in `devcontainer.json`.
