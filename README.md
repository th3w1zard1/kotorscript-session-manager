# KOTORScript Session Manager

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-latest-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight, production-ready FastAPI service for managing KOTORModSync telemetry sessions and authentication. Designed to integrate seamlessly with the [bolabaden.org infrastructure](https://bolabaden.org).

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [Development](#development)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

## Overview

This repository provides a session management service for KOTORModSync clients, handling secure telemetry ingestion, HMAC authentication, and session state management. It's part of a larger observability infrastructure built on OpenTelemetry (OTLP), Prometheus, and Grafana.

The service:
- **Receives and validates** telemetry requests with HMAC-SHA256 signatures
- **Prevents replay attacks** with timestamp validation (5-minute window)
- **Enforces rate limiting** (10 req/sec per IP) via Traefik
- **Serves dynamic HTML** for session status pages
- **Provides health checks** for container orchestration
- **Persists state** through secure telemetry collection

## Features

✅ **FastAPI** - Modern, high-performance async Python web framework  
✅ **Health Check Endpoint** - `/health` for container orchestration  
✅ **Session Management** - Dynamic HTML template serving with fallback defaults  
✅ **Minimal Footprint** - Lightweight, single-file application  
✅ **Docker Ready** - Production-grade containerization included  
✅ **Configurable** - Environment-driven configuration  
✅ **Security-First** - Supports HMAC authentication & secure telemetry pipeline  
✅ **Well-Documented** - Comprehensive guides for integration & deployment  

## Quick Start

### Prerequisites

- Python 3.8 or higher
- FastAPI
- uvicorn
- Docker (for containerized deployment)

### Installation

```bash
# Clone the repository
git clone https://github.com/th3w1zard1/kotorscript-session-manager.git
cd kotorscript-session-manager

# Install dependencies
pip install -r requirements.txt
# Or manually:
pip install fastapi uvicorn
```

### Running Locally

```bash
# Start the service on default port 8080
python session_manager.py

# Start on a custom port
SESSION_MANAGER_PORT=9000 python session_manager.py

# Run with uvicorn directly for development
uvicorn session_manager:app --reload --host 0.0.0.0 --port 8080
```

Visit `http://localhost:8080` to see the session manager interface.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main session manager page (serves `index.html` or fallback) |
| `/health` | GET | Service health check endpoint |
| `/waiting` | GET | Waiting/loading page (serves `waiting.html` or fallback) |

### Response Examples

**Health Check:**
```bash
curl http://localhost:8080/health
```
```json
{"status": "healthy"}
```

**Main Page:**
```bash
curl http://localhost:8080/
```
Returns HTML content from `/tmp/templates/index.html` or default HTML.

## Architecture

This service integrates into a secure telemetry pipeline:

```
KOTORModSync Clients
       ↓ (HTTPS)
    Traefik (TLS Termination)
       ↓
Session Manager (This Service)
       ↓ (HMAC Auth Validation)
  OTLP Collector
       ↓
 VictoriaMetrics/Prometheus
       ↓
    Grafana
```

### Telemetry Flow

1. **Client sends telemetry** - KOTORModSync clients make HTTPS requests with HMAC-SHA256 signatures
2. **Traefik routes** - Reverse proxy handles TLS termination and rate limiting
3. **Session Manager processes** - Authenticates requests, validates timestamps, prevents replays
4. **Metrics collected** - OTLP Collector receives validated telemetry data
5. **Time-series storage** - Prometheus/VictoriaMetrics stores metrics
6. **Visualization** - Grafana displays dashboards with real-time data

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_MANAGER_PORT` | `8080` | HTTP listen port for the service |

### Template Locations

The service looks for HTML templates in `/tmp/templates/`:

- **`/tmp/templates/index.html`** - Main page served at `/`
- **`/tmp/templates/waiting.html`** - Waiting page served at `/waiting`

If templates don't exist at these paths, the service returns default fallback HTML.

## Deployment

### Docker Compose

The service is designed to work with the bolabaden.org Docker Compose stack:

```yaml
services:
  session-manager:
    image: session-manager:latest
    container_name: session_manager
    environment:
      SESSION_MANAGER_PORT: 8080
    ports:
      - "8080:8080"
    networks:
      - publicnet
      - backend
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://127.0.0.1:8080/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    labels:
      traefik.enable: "true"
      traefik.http.routers.session-manager.rule: "Host(`session-manager.$DOMAIN`)"
      traefik.http.services.session-manager.loadbalancer.server.port: "8080"
```

### Kubernetes

For Kubernetes deployments, refer to the charts directory in the parent infrastructure.

## Documentation

Comprehensive documentation is available in the `.github/` and `docs/` directories:

| Document | Purpose |
|----------|---------|
| [Client Integration Guide](docs/KOTORMODSYNC_CLIENT_INTEGRATION.md) | How to integrate KOTORModSync clients with HMAC signing |
| [Security Summary](docs/KOTORMODSYNC_SECURITY_SUMMARY.md) | Complete security architecture and best practices |
| [Telemetry Setup](docs/KOTORMODSYNC_TELEMETRY_SETUP.md) | Server-side OTLP collector configuration |
| [OTLP Quickstart](docs/OTLP_QUICKSTART.md) | Quick deployment guide for the OTLP stack |
| [Maintenance Guide](docs/MAINTENANCE.md) | Operational procedures and troubleshooting |
| [Secrets Quick Start](docs/SECRETS_QUICK_START.txt) | Secret management best practices |
| [Sync Analysis](SYNC_ANALYSIS.md) | Docker Compose vs Nomad synchronization (41 services tracked) |

## Development

### Project Structure

```
kotorscript-session-manager/
├── session_manager.py              # Main FastAPI application
├── README.md                       # This file
├── .cursorrules                    # Development guidelines
├── .gitignore                      # Git ignore rules
├── CONTRIBUTING.md                 # Contribution guidelines
├── SECURITY.md                     # Security policy
├── docs/                          # Comprehensive documentation
│   ├── KOTORMODSYNC_CLIENT_INTEGRATION.md
│   ├── KOTORMODSYNC_SECURITY_SUMMARY.md
│   ├── KOTORMODSYNC_TELEMETRY_SETUP.md
│   ├── OTLP_QUICKSTART.md
│   ├── MAINTENANCE.md
│   └── SECRETS_QUICK_START.txt
├── .github/                       # GitHub configuration
│   ├── README.md                  # Extended documentation
│   ├── dependabot.yml             # Automated dependency updates
│   ├── SECURITY.md                # Security advisories
│   └── workflows/                 # CI/CD pipelines
│       ├── deploy.yml             # Deployment workflow
│       ├── docker-build.yml       # Docker build workflow
│       ├── e2e.yml                # End-to-end tests
│       ├── llm-fallbacks-ci.yml   # LLM integration tests
│       └── test-stack.yml         # Stack tests
└── .gitmodules                    # Git submodule configuration
```

### Development Workflow

1. **Create a branch** - `git checkout -b feature/my-feature`
2. **Make changes** - Edit `session_manager.py` or documentation
3. **Test locally** - `python session_manager.py`
4. **Commit** - `git commit -m "feat: describe your changes"`
5. **Push** - `git push origin feature/my-feature`
6. **Create a PR** - GitHub will run CI/CD workflows automatically

### Running Tests

```bash
# Run the application with auto-reload for development
uvicorn session_manager:app --reload

# Run end-to-end tests (via GitHub Actions)
# See .github/workflows/e2e.yml
```

### Code Style

This project follows Python best practices:

- **Type hints** - All functions should have type annotations
- **Docstrings** - Comprehensive docstrings for all functions
- **PEP 8** - Follow PEP 8 naming conventions
- **Async-first** - Use async/await for I/O operations

Refer to [.cursorrules](.cursorrules) for detailed development guidelines.

## Security

### HMAC Authentication

All telemetry requests are secured with:

- **HMAC-SHA256 signatures** - Cryptographic request signing
- **Timestamp validation** - Prevents replay attacks (5-minute window)
- **Rate limiting** - 10 requests/second per IP (via Traefik)
- **TLS encryption** - HTTPS-only communication (via Traefik)
- **Secret rotation** - Supports rotating signing keys without downtime

### Security Policy

For security issues, please see [SECURITY.md](SECURITY.md) for responsible disclosure procedures.

### Compliance

- No hardcoded secrets - All secrets managed via environment or secure storage
- Minimal dependencies - Only FastAPI and uvicorn required
- Health checks enabled - Automatic container restart on failure
- Regular updates - Dependabot enabled for automated security updates

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- How to report bugs
- How to suggest enhancements
- How to submit pull requests
- Code of conduct

### Development Requirements

- Python 3.8+
- Git
- Docker (for testing containerized deployments)

### Git Workflow

This repository uses **conventional commits**:

- `feat:` - New features
- `fix:` - Bug fixes
- `refactor:` - Code refactoring
- `docs:` - Documentation updates
- `test:` - Test additions/changes
- `chore:` - Build/dependency changes

Example: `git commit -m "feat: add session timeout configuration"`

## CI/CD

The repository includes GitHub Actions workflows for:

- **Docker Build** - Build and push Docker images
- **E2E Tests** - End-to-end testing of the service
- **LLM Fallbacks** - Integration testing with language model services
- **Stack Tests** - Full integration tests with the bolabaden infrastructure
- **Dependabot** - Automated security and dependency updates

See [.github/workflows/](.github/workflows/) for workflow definitions.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Support

### Documentation

Start with the [docs/](docs/) directory for comprehensive guides on integration, security, and deployment.

### Troubleshooting

Common issues and solutions are documented in [MAINTENANCE.md](docs/MAINTENANCE.md).

### Questions?

- Open an [issue](https://github.com/th3w1zard1/kotorscript-session-manager/issues) for bug reports
- Start a [discussion](https://github.com/th3w1zard1/kotorscript-session-manager/discussions) for questions

## Related Projects

- **[bolabaden.org](https://bolabaden.org)** - Parent infrastructure project
- **[KOTORModSync](https://github.com/th3w1zard1/KOTORModSync)** - Telemetry client
- **[llm-fallbacks](https://github.com/th3w1zard1/llm_fallbacks)** - LLM service fallback handling
- **[HoloLSP](https://github.com/OldRepublicDevs/HoloLSP)** - Language Server Protocol for KOTOR

## Acknowledgments

This project is part of the bolabaden.org infrastructure initiative, designed to provide secure, scalable telemetry and monitoring for distributed systems.

---

**Last Updated:** February 28, 2026  
**Status:** Active Development  
**Maintainer:** [@th3w1zard1](https://github.com/th3w1zard1)
