# Security Policy

## Supported Versions

We actively maintain and provide security updates for the main branch of this repository.

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in **our code** (not vendored dependencies), please report it by:

1. Opening a private security advisory on GitHub
2. Or emailing the repository maintainer directly

**Please do not** open public issues for security vulnerabilities.

## Security Scanning & Vendored Code

### What We Scan

GitHub security scanning is enabled for:
- Root project dependencies (`package.json`, `package-lock.json`)
- Active project code in `/projects`
- Infrastructure scripts in `/scripts`
- Docker images and configurations

### What We Don't Scan

The following directories contain **vendored third-party code** that is not actively maintained as part of this project:

- `src/firecrawl/` - Firecrawl web scraping service (reference)
- `src/hedgedoc/` - HedgeDoc collaborative markdown editor (reference)
- `src/AIOStreams/` - AIO Streams addon (reference)
- `src/fetch-mcp/` - Fetch MCP server (reference)
- `src/mcp-webresearch/` - MCP Web Research server (reference)
- `src/markdownify-mcp/` - Markdownify MCP server (reference)
- `src/zurg/` - Zurg real-debrid client (reference)
- `vendor/` - All vendored dependencies
- `reference/` - Reference implementations and examples

These projects are:
1. **Not deployed** in our production environment
2. **Not actively maintained** by this repository
3. **Included for reference only**
4. **Marked as `linguist-vendored`** in `.gitattributes`

If you're using code from these directories, you should:
- Check the original upstream repositories for security updates
- Follow the upstream project's security policies
- Update your local copies from upstream sources

### Our Security Practices

1. **Automated Updates**: Dependabot runs weekly to update dependencies
2. **Log Rotation**: Docker logs are automatically rotated (10MB × 3 files)
3. **Resource Limits**: All services have memory limits configured
4. **Automated Cleanup**: Weekly maintenance removes unused Docker resources
5. **Disk Monitoring**: Daily checks alert when disk usage exceeds 85%

### Dependency Management

#### Root Dependencies (Actively Maintained)
```json
{
  "@next/mdx": "^15.3.5",
  "gray-matter": "^4.0.3",
  "next-mdx-remote": "^5.0.0",
  "remark": "^15.0.1",
  "remark-html": "^16.0.1"
}
```

These are kept up-to-date via Dependabot and manual updates.

#### Docker Images

We use official Docker images from:
- `docker.io` (Docker Hub)
- `ghcr.io` (GitHub Container Registry)  
- `gcr.io` (Google Container Registry)

All images are pinned to specific versions or tags in `docker-compose.yml`.

### Security Hardening

See `docs/MAINTENANCE.md` for:
- Automated maintenance schedules
- Log rotation configuration
- Cache cleanup procedures
- Emergency recovery procedures

### Questions?

If you have questions about our security practices or this policy, please open a discussion on GitHub.

---

**Note**: This repository is for personal/homelab use. It is not intended for production enterprise deployments. Use at your own risk.

