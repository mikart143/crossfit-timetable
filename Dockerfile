# ---------- builder ----------
FROM almalinux/9-minimal:9.7 AS builder

WORKDIR /app

# Install build dependencies
RUN microdnf install -y \
    gcc \
    gcc-c++ \
    make \
    openssl-devel \
    pkg-config \
    && microdnf clean all

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Copy source code
COPY src ./src

# Build for release
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/app/target \
    cargo build --release && \
    cp /app/target/release/crossfit-timetable /app/crossfit-timetable


# ---------- final ----------
FROM almalinux/9-micro:9.7 AS final

# Capture platform information
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH

# Copy CA certificates (rustls is pure Rust, no C libs needed)
COPY --from=builder /etc/pki/tls/certs/ca-bundle.crt /etc/pki/tls/certs/ca-bundle.crt

# Set SSL certificate environment variables
ENV SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt \
    SSL_CERT_DIR=/etc/pki/tls/certs

# Copy the compiled binary
COPY --from=builder /app/crossfit-timetable /usr/local/bin/crossfit-timetable

# Use non-root user
USER 65532:65532

# Run the binary
CMD ["/usr/local/bin/crossfit-timetable"]