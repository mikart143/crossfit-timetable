.PHONY: setup install-tools build build-release run test clean docker-build docker-run help

help:
	@echo "Available targets:"
	@echo "  make setup          - Install tools and build the project"
	@echo "  make install-tools  - Install cargo utilities (cargo-binstall)"
	@echo "  make build          - Build debug binary"
	@echo "  make build-release  - Build optimized release binary"
	@echo "  make run            - Run the project"
	@echo "  make test           - Run tests"
	@echo "  make clean          - Remove build artifacts"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-run     - Run Docker container"
	@echo "  make help           - Show this help message"

setup: install-tools build

install-tools:
	rustup component add llvm-tools-preview --toolchain nightly
	cargo install cargo-binstall
	cargo binstall -y cargo-llvm-cov
	cargo binstall -y --secure cargo-nextest

build:
	cargo build

build-release:
	cargo build --release

run:
	cargo run

test:
	cargo nextest run

clean:
	cargo clean

docker-build:
	docker build -t crossfit-timetable .

docker-run: docker-build
	docker run -p 8080:8080 crossfit-timetable

format:
	cargo fmt --all
