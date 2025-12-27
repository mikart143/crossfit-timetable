# Dev Container Configuration

This directory contains the configuration for the VS Code Dev Container for the CrossFit Timetable project.

## What's Included

### Base Image
- AlmaLinux 9
- Git and common development tools

### VS Code Extensions
- **Rust Support**: rust-analyzer, crates
- **Linting & Formatting**: rustfmt, clippy
- **Configuration Files**: Even Better TOML, YAML
- **Development**: GitHub Copilot, REST Client, vscode-lldb (debugger)

### Rust Environment
- **Rust Toolchain**: Installed via Dev Container features (minimal profile)
- **Components**: rust-analyzer, rust-src, rustfmt, clippy
- **Build Dependencies**: gcc, gcc-c++, make, pkgconf-pkg-config, openssl-devel (installed via bash-command feature)

### Docker
- **Docker-in-Docker**: Docker CLI available for running and managing containers inside the dev container

### Port Forwarding
- Port 8080 is automatically forwarded

## Getting Started

1. Open the project in VS Code
2. When prompted, click "Reopen in Container" or run the command "Dev Containers: Reopen in Container"
3. Wait for the container to build and features to install
4. Start developing!

## Running the Application

```bash
# Build and run the application
cargo run

# Build in release mode
cargo build --release

# Run tests
cargo test

# Run clippy linter
cargo clippy

# Format code
cargo fmt
```

## Environment Variables

Configuration is loaded from environment variables or a `.env` file. Create a `.env` file in your workspace root if needed.

## Customization

You can customize the dev container by editing:
- `.devcontainer/devcontainer.json` - Main configuration and feature setup

## Troubleshooting

### Container Build Fails
Try rebuilding the container: Command Palette → "Dev Containers: Rebuild Container"

### Linking Errors (OpenSSL)
The dev container automatically installs `openssl-devel` via the bash-command feature. If you still get linking errors, ensure the container was fully rebuilt.

### Port Already in Use
If port 8080 is already in use, you can change the forwarded ports in `devcontainer.json`.
