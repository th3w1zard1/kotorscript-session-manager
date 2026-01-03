# Docker Compose ↔ Nomad Synchronization Analysis

Generated: $(date)

## Summary

This analysis compares **active services** (no profiles) in Docker Compose vs Nomad configurations.

---

## ✅ Services Present in BOTH (41 services)

These are correctly synchronized:
- aiostreams
- autokuma
- bolabaden-nextjs
- cloudflare-ddns
- crowdsec
- dockerproxy-ro
- dockerproxy-rw
- dozzle
- firecrawl
- flaresolverr
- gptr
- headscale-server
- homepage
- ip-checker-warp
- jackett
- litellm
- litellm-postgres
- logrotate-traefik
- mcpo
- mongodb
- nginx-traefik-extensions
- nuq-postgres
- open-webui
- playwright-service
- portainer
- prowlarr
- rclone
- rclone-init
- redis
- searxng
- session-manager
- stremio
- stremthru
- tinyauth
- traefik
- warp-nat-gateway
- warp_router
- watchtower
- whoami

---

## ❌ Missing from NOMAD (14 services in Docker)

### 1. **Metrics Stack** (10 services - NOT in Nomad)
```yaml
# Docker: compose/docker-compose.metrics.yml
services:
  blackbox-exporter:     # Prometheus blackbox exporter
  cadvisor:              # Container metrics
  grafana:               # Visualization
  init_prometheus:       # Init container
  init_victoriametrics:  # Init container  
  loki:                  # Log aggregation
  node_exporter:         # Host metrics
  prometheus:            # Metrics database
  promtail:              # Log shipper
  victoriametrics:       # Time series database
```
**Status**: Entire metrics stack is in Docker but NOT in Nomad
**Note**: There's no `metrics.nomad.hcl` file in the nomad directory

### 2. **docker-gen-failover**
```yaml
# Docker: compose/docker-compose.coolify-proxy.yml
  docker-gen-failover:
    profiles:
      - extras
    image: docker.io/nginx:alpine
    container_name: docker-gen-failover
    # Failover nginx for coolify proxy
```
**Status**: In Docker coolify-proxy but NOT in Nomad
**Action Needed**: Add to Nomad coolify proxy group

### 3. **headscale** (UI service)
```yaml
# Docker: compose/docker-compose.headscale.yml
  headscale:
    depends_on:
      - headscale-server
    image: ghcr.io/gurucomputing/headscale-ui
    container_name: headscale
    # THIS IS THE UI SERVICE
```
**Docker has**: `headscale` (UI) + `headscale-server` (backend)
**Nomad has**: `headscale-ui` + `headscale-server`
**Status**: ✅ BOTH HAVE BOTH - just named differently
**Issue**: Docker names UI as "headscale", Nomad names it "headscale-ui"
**Action**: Rename in Docker to match Nomad OR vice versa

### 4. **telemetry-auth**
```yaml
# Docker: docker-compose.yml (root)
  telemetry-auth:
    build:
      context: projects/kotormodsync/telemetry-auth
      dockerfile: Dockerfile
    image: bolabaden/kotormodsync-telemetry-auth:latest
    container_name: telemetry-auth-test
    hostname: telemetry-auth
    ports:
      - "8080:8080"
    secrets:
      - signing_secret
```
**Status**: In Docker root but NOT in Nomad
**Action Needed**: Add to Nomad

### 5. **warp-net-init**
```yaml
# Docker: compose/docker-compose.warp-nat-routing.yml
  warp-net-init:
    # Creates the warp-nat-net network if it doesn't exist
    image: docker:cli
    container_name: warp-net-init
    network_mode: host
    command: [creates network]
    restart: "no"
```
**Status**: In Docker but NOT in Nomad
**Reason**: Nomad likely handles network creation differently
**Action**: Verify if Nomad needs this or if network creation is handled elsewhere

---

## ❌ Missing from DOCKER (6 services in Nomad)

### 1. **authentik** services (3 services)
```hcl
# Nomad: docker-compose.nomad.hcl
group "authentik-services" {
  task "authentik-postgresql"
  task "authentik"
  task "authentik-worker"
}
```

```yaml
# Docker: compose/docker-compose.authentik.yml EXISTS
# BUT: docker-compose.yml line 50 has it COMMENTED OUT:
include:
#  - compose/docker-compose.authentik.yml  # ← COMMENTED
```
**Status**: Nomad HAS it, Docker HAS the file but it's DISABLED
**Action Needed**: Uncomment in Docker OR remove from Nomad

### 2. **mcp-proxy**
```hcl
# Nomad: docker-compose.nomad.hcl
group "mcp-proxy-group" {
  task "mcp-proxy"
}
```

```yaml
# Docker: compose/docker-compose.llm.yml
  mcp-proxy:
    profiles:
      - extras  # ← HAS PROFILE (excluded from active services)
    image: ghcr.io/tbxark/mcp-proxy
```
**Status**: Docker HAS it but with `profiles: [extras]`, so it's disabled by default
**Nomad**: Active (no profile equivalent)
**Action Needed**: Enable in Docker (remove profile) OR disable in Nomad

### 3. **qdrant**
```hcl
# Nomad: docker-compose.nomad.hcl
group "qdrant-group" {
  task "qdrant"
}
```

```yaml
# Docker: compose/docker-compose.llm.yml
  qdrant:
    profiles:
      - extras  # ← HAS PROFILE (excluded from active services)
    image: qdrant/qdrant
```
**Status**: Docker HAS it but with `profiles: [extras]`, so it's disabled by default
**Nomad**: Active (no profile equivalent)
**Action Needed**: Enable in Docker (remove profile) OR disable in Nomad

---

## 🔧 Configuration Differences

### Warp Routing
**Docker has**:
- `warp-net-init` (network creator, runs once)
- `warp-nat-gateway` (WARP container)
- `warp_router` (routing controller)
- `ip-checker-warp` (test container)

**Nomad has**:
- `warp-nat-gateway` (WARP container)
- `warp_router` (routing controller)
- `ip-checker-warp` (test container)
- ❌ Missing: `warp-net-init`

**Note**: Nomad warp-nat-routing group has `count = 0` (DISABLED)

---

## 🎯 Action Items

### Priority 1: Clarify User Intent
1. **Authentik**: Enable in Docker or remove from Nomad?
2. **mcp-proxy**: Enable in Docker or remove from Nomad?
3. **qdrant**: Enable in Docker or remove from Nomad?
4. **telemetry-auth**: Add to Nomad or remove from Docker?

### Priority 2: Add Missing Services
5. **Metrics Stack**: Create `metrics.nomad.hcl` with all 10 services
6. **docker-gen-failover**: Add to Nomad coolify-proxy
7. **warp-net-init**: Verify if Nomad needs this

### Priority 3: Fix Naming Inconsistencies
8. **headscale UI**: Standardize naming (both have it, just different names)
   - Docker: `headscale` (container name for UI)
   - Nomad: `headscale-ui` (task name for UI)

---

## 📊 Statistics

- **Total Docker services (active, no profiles)**: 53
- **Total Nomad services**: 45
- **Services in both**: 41 (77%)
- **Docker only**: 14 (26%)
- **Nomad only**: 6 (13%)

---

## Next Steps

1. **User decision** on authentik, mcp-proxy, qdrant, telemetry-auth
2. **Create** `metrics.nomad.hcl` for the entire metrics stack
3. **Add** missing services to Nomad (telemetry-auth, docker-gen-failover, warp-net-init)
4. **Remove or enable** services based on user preference
5. **Test** and validate all changes
6. **Commit** to git with proper commit messages

