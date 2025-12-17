# ---------- builder ----------
FROM almalinux/9-minimal:9.7 AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/python \
    UV_PYTHON_PREFERENCE=only-managed

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=/app/pyproject.toml,readonly \
    --mount=type=bind,source=uv.lock,target=/app/uv.lock,readonly \
    uv sync --locked --no-install-project --no-dev --no-editable

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable


# ---------- final ----------
FROM almalinux/9-micro:9.7  AS final

# Capture platform information
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH

# Copy CA certificates from builder (which has them installed)
COPY --from=builder /etc/pki /etc/pki
COPY --from=builder /etc/ssl /etc/ssl

# Set SSL certificate environment variables
ENV SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt \
    SSL_CERT_DIR=/etc/pki/tls/certs \
    REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt

# distroless nonroot user
COPY --from=builder --chown=nonroot:nonroot /python /python
COPY --from=builder --chown=nonroot:nonroot /app /app

# Use the venv's Python (follows the symlink into /python)
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "crossfit_timetable.main:app", "--host", "0.0.0.0", "--port", "8000"]