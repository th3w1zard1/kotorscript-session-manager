# KOTORScript Session Manager

A lightweight FastAPI-based session management service designed to work with the bolabaden.org infrastructure, specifically for handling KOTORModSync telemetry and authentication.

## Overview

This repository is part of the larger [bolabaden.org infrastructure](https://bolabaden.org) and provides a simple HTTP service for managing session states and serving basic HTML templates. It's designed to work in conjunction with:

- **OpenTelemetry (OTLP) Collector** - Receives telemetry data from KOTORModSync clients
- **Authentication Services** - HMAC-SHA256 signature verification for secure telemetry ingestion
- **Traefik** - Reverse proxy for routing and TLS termination

## Features

- ✅ **Health Check Endpoint** - `/health` returns service status
- ✅ **Session Management** - Basic HTML template serving
- ✅ **Lightweight** - Built with FastAPI for minimal resource usage
- ✅ **Docker Ready** - Designed to run in containerized environments
- ✅ **Configurable Port** - Environment variable driven configuration

## Quick Start

### Prerequisites

- Python 3.8+
- FastAPI
- uvicorn

### Installation

```bash
# Clone the repository
git clone https://github.com/th3w1zard1/kotorscript-session-manager.git
cd kotorscript-session-manager

# Install dependencies
pip install fastapi uvicorn
```

### Running Locally

```bash
# Default port 8080
python session_manager.py

# Custom port via environment variable
SESSION_MANAGER_PORT=9000 python session_manager.py
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check endpoint |
| `/` | GET | Main session manager page |
| `/waiting` | GET | Waiting/loading page |

## Architecture

This service is part of a larger telemetry infrastructure:

```
KOTORModSync Clients
       ↓
  HTTPS (Traefik)
       ↓
HMAC Auth Service ← kotorscript-session-manager
       ↓
OTLP Collector
       ↓
  Prometheus
       ↓
    Grafana
```

### Security Architecture

The service integrates with a secure telemetry pipeline that uses:

- **HMAC-SHA256 Signing** - All telemetry requests are signed
- **Timestamp Validation** - Prevents replay attacks (5-minute window)
- **Rate Limiting** - 10 requests/second per IP via Traefik
- **Secret Rotation** - Supports rotating signing secrets without downtime

For detailed security information, see the [Security Summary](docs/KOTORMODSYNC_SECURITY_SUMMARY.md).

## Documentation

The `docs/` directory contains comprehensive guides:

- **[Client Integration Guide](docs/KOTORMODSYNC_CLIENT_INTEGRATION.md)** - How to integrate KOTORModSync clients with HMAC signing
- **[Security Summary](docs/KOTORMODSYNC_SECURITY_SUMMARY.md)** - Complete security architecture and best practices
- **[Telemetry Setup](docs/KOTORMODSYNC_TELEMETRY_SETUP.md)** - Server-side OTLP collector configuration
- **[OTLP Quickstart](docs/OTLP_QUICKSTART.md)** - Quick deployment guide for the OTLP stack
- **[Maintenance Guide](docs/MAINTENANCE.md)** - Operational procedures and troubleshooting
- **[Secrets Quick Start](docs/SECRETS_QUICK_START.txt)** - Secret management guide

### Additional Resources

- **[SYNC_ANALYSIS.md](SYNC_ANALYSIS.md)** - Docker Compose vs Nomad synchronization analysis (41 services tracked)

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_MANAGER_PORT` | `8080` | Port the service listens on |

### Template Locations

Templates are loaded from `/tmp/templates/`:
- `/tmp/templates/index.html` - Main page
- `/tmp/templates/waiting.html` - Waiting page

If templates don't exist, fallback HTML is served.

## Deployment

### Docker

The service is designed to run as part of a Docker Compose stack with the bolabaden.org infrastructure.

### Integration Points

1. **Traefik** - Reverse proxy routing to the service
2. **OTLP Collector** - Receives forwarded telemetry after authentication
3. **Prometheus** - Stores metrics from the OTLP collector
4. **Grafana** - Visualizes telemetry data

## Development

### Project Structure

```
.
├── session_manager.py           # Main FastAPI application
├── docs/                        # Comprehensive documentation
│   ├── KOTORMODSYNC_CLIENT_INTEGRATION.md
│   ├── KOTORMODSYNC_SECURITY_SUMMARY.md
│   ├── KOTORMODSYNC_TELEMETRY_SETUP.md
│   ├── OTLP_QUICKSTART.md
│   ├── MAINTENANCE.md
│   └── SECRETS_QUICK_START.txt
├── SYNC_ANALYSIS.md            # Service synchronization analysis
└── .github/                     # GitHub configuration
    ├── dependabot.yml          # Automated dependency updates
    └── workflows/              # CI/CD pipelines
```

### Git Submodules

This repository includes submodules for related services:
- `src/cloudflare-ddns` - Cloudflare DDNS updater
- `ai-researchwizard` - AI research assistant integration

To clone with submodules:

```bash
git clone --recursive https://github.com/th3w1zard1/kotorscript-session-manager.git
```

## Contributing

Contributions are welcome! Please see our [Security Policy](.github/SECURITY.md) for reporting vulnerabilities.

### Open Issues

This repository currently has **5 open issues** (Dependabot PRs for updating GitHub Actions).

[View all open issues →](https://github.com/th3w1zard1/kotorscript-session-manager/issues)

## Related Projects

- **[KOTORModSync](https://github.com/th3w1zard1/KOTORModSync)** - The client application that sends telemetry to this service
- **[bolabaden.org Infrastructure](https://bolabaden.org)** - The larger infrastructure this service is part of

## License

This project is part of the bolabaden.org infrastructure. Please check the repository for specific license information.

## Support

For issues related to:
- **Session Manager**: Open an issue in this repository
- **Telemetry Setup**: See [docs/KOTORMODSYNC_TELEMETRY_SETUP.md](docs/KOTORMODSYNC_TELEMETRY_SETUP.md)
- **Client Integration**: See [docs/KOTORMODSYNC_CLIENT_INTEGRATION.md](docs/KOTORMODSYNC_CLIENT_INTEGRATION.md)
- **Security Concerns**: See our [Security Policy](.github/SECURITY.md)

## Monitoring

Service health can be monitored via:
- `/health` endpoint (returns `{"status": "healthy"}`)
- Docker container logs
- Integration with Uptime Kuma (when deployed)

---

**Last Updated:** February 2026  
**Repository:** [th3w1zard1/kotorscript-session-manager](https://github.com/th3w1zard1/kotorscript-session-manager)
