# AGENTS.md

## Cursor Cloud specific instructions

### Overview

This is a single-file FastAPI application (`session_manager.py`) that manages ephemeral VS Code (OpenVSCode Server) containers for KOTOR game modding. Dependencies are listed in `requirements.txt`.

### Running the application

```bash
# Templates must be in /tmp/templates/ before starting
mkdir -p /tmp/templates && cp index.html waiting.html /tmp/templates/

# Start the dev server (default port 8080)
python session_manager.py

# Or with auto-reload for development
uvicorn session_manager:app --reload --host 0.0.0.0 --port 8080
```

### Key endpoints

- `GET /` — Landing page (Jinja2 template)
- `GET /health` — Returns `OK`
- `GET /capacity` — JSON with session counts
- `POST /new` — Creates a new session container (requires Docker)

### Docker requirement

The `/new` endpoint and session lifecycle features require a running Docker daemon with a `publicnet` network (`docker network create publicnet`). Without Docker, the health endpoint and landing page still work.

### Linting

No formal lint config exists in the repo. Use `ruff check session_manager.py` for quick lint checks. Existing code has pre-existing unused-import warnings (F401).

### Gotchas

- Templates directory is `/tmp/templates/` (not the repo root). The app reads `index.html` and `waiting.html` from there, falling back to default HTML if missing.
- Python packages install to `~/.local/bin` — ensure this is on `PATH`.
- No Python test suite (pytest) exists; CI validates via lint, compilation, and endpoint smoke tests.

### CI Workflows

- `test-stack.yml` — Lint + compile + endpoint smoke tests (runs on every PR/push)
- `e2e.yml` — End-to-end endpoint tests (runs on non-markdown changes)
- `deploy.yml` — Deploy static HTML to GitHub Pages
- `docker-build.yml` — Build and push Docker image to GHCR
- `.github/` was previously in `.gitignore`, which blocked workflow updates; it has been removed.
