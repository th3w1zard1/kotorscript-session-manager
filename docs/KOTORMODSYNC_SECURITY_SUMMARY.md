# KOTORModSync Telemetry Security Summary

## Overview

This document explains the complete security architecture for KOTORModSync telemetry that prevents abuse while keeping your public GitHub repository clean of secrets.

## The Challenge

**Problem:** How do you authenticate a public open-source application (KOTORModSync) to send telemetry to your server (`otlp.bolabaden.org`) without:
1. Exposing secrets in the public GitHub repository
2. Breaking the build for contributors without the secret
3. Allowing anyone to send fake/spam telemetry

**Solution:** HMAC-SHA256 request signing with build-time secret injection.

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ KOTORModSync Client (User's Computer)                      │
│                                                             │
│ 1. Load signing secret from:                               │
│    a) Environment variable (highest priority)              │
│    b) Local config file (~/.config/kotormodsync/)          │
│    c) Embedded secret (official builds only)               │
│                                                             │
│ 2. Compute HMAC-SHA256:                                    │
│    message = "POST|/v1/metrics|{timestamp}|{session_id}"   │
│    signature = HMAC-SHA256(secret, message)                │
│                                                             │
│ 3. Send OTLP request with headers:                         │
│    X-KMS-Signature: {signature}                            │
│    X-KMS-Timestamp: {timestamp}                            │
│    X-KMS-Session-ID: {session_id}                          │
│    X-KMS-Client-Version: {version}                         │
└──────────────────┬──────────────────────────────────────────┘
                   │ HTTPS POST
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Traefik (otlp.bolabaden.org)                               │
│                                                             │
│ ┌─────────────────────────────────────────────────┐       │
│ │ ForwardAuth Middleware                          │       │
│ │ Forwards to: http://kotormodsync-auth:8080      │       │
│ └───────────────────┬─────────────────────────────┘       │
└─────────────────────┼───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Authentication Service (kotormodsync-auth)                  │
│                                                             │
│ 1. Extract headers from request                            │
│ 2. Validate timestamp (prevent replay attacks)             │
│ 3. Compute expected signature:                             │
│    expected = HMAC-SHA256(server_secret, message)          │
│ 4. Compare signatures (constant-time)                      │
│ 5. Return 200 (valid) or 401/403 (invalid)                 │
└──────────────────┬──────────────────────────────────────────┘
                   │ If valid (200)
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ OpenTelemetry Collector (otel-collector)                   │
│ Receives telemetry and exports to Prometheus               │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ Prometheus → Grafana                                        │
│ Store and visualize metrics                                │
└─────────────────────────────────────────────────────────────┘
```

## Security Features

### 1. Secret Management

**On Server (bolabaden.org):**
- Secret stored in: `/home/ubuntu/my-media-stack/volumes/kotormodsync_signing_secret.txt`
- Mounted as Docker secret (read-only)
- Never exposed in logs or error messages
- Easy rotation without code changes

**In KOTORModSync Source Code:**
- Secret **NEVER** committed to git
- `.gitignore` excludes all secret files
- Template file (`EmbeddedSecrets.cs.example`) shows structure
- Actual secret file (`EmbeddedSecrets.cs`) is generated during CI/CD

**In GitHub Actions:**
- Secret stored as repository secret: `KOTORMODSYNC_SIGNING_SECRET`
- Injected during official builds only
- Not available to pull requests from forks (security feature)

### 2. HMAC Signing

**Why HMAC-SHA256?**
- Industry standard (used by AWS, Stripe, GitHub webhooks)
- Cryptographically secure
- Prevents tampering (can't forge without secret)
- Fast to compute

**Message Format:**
```
POST|{path}|{timestamp}|{session_id}
```

Example:
```
POST|/v1/metrics|1697234567|abc123-def456-session-id
HMAC-SHA256(secret, above) = a1b2c3d4e5f6...
```

**Why include timestamp and session_id?**
- Timestamp: Prevents replay attacks (5-minute window)
- Session ID: Prevents cross-session replay
- Path: Prevents endpoint confusion

### 3. Attack Prevention

| Attack Type | Prevention Method | How It Works |
|-------------|-------------------|--------------|
| **Replay Attack** | Timestamp validation | Requests > 5 minutes old rejected |
| **Brute Force** | Rate limiting | Max 10 req/s per IP (Traefik) |
| **Secret Extraction** | Secret rotation | Rotate every 90 days, revoke if compromised |
| **Timing Attack** | Constant-time comparison | Uses `hmac.compare_digest()` |
| **Spam Telemetry** | Signature required | Unsigned requests rejected at edge |
| **Fork Abuse** | CI secret isolation | Forks don't have access to secret |

### 4. Graceful Degradation

**Without Secret:**
- Application still builds ✅
- Application still runs ✅
- All features work ✅
- Only telemetry is disabled ⚠️

**Why this matters:**
- Contributors can build without secrets
- Development doesn't require production credentials
- Fork maintainers can use their own telemetry endpoints
- No "broken" builds for external contributors

## Secret Storage: Three Tiers

### Tier 1: Production (GitHub Actions)
```yaml
# .github/workflows/build.yml
- name: Inject Telemetry Secret (Official Builds Only)
  if: github.event_name == 'release'
  env:
    TELEMETRY_SECRET: ${{ secrets.KOTORMODSYNC_SIGNING_SECRET }}
  run: |
    # Generate EmbeddedSecrets.cs with real secret
    echo "namespace KOTORModSync.Telemetry {" > EmbeddedSecrets.cs
    echo "  internal const string TELEMETRY_SIGNING_KEY = \"$TELEMETRY_SECRET\";" >> EmbeddedSecrets.cs
    echo "}" >> EmbeddedSecrets.cs

- name: Build (Official)
  run: dotnet build -c Release /p:DefineConstants="OFFICIAL_BUILD"
```

**Security:**
- ✅ Secret only in GitHub secrets (encrypted)
- ✅ Only available to maintainers
- ✅ Not available to pull requests from forks
- ✅ Automatically injected during release builds

### Tier 2: Development (Local Config)
```csharp
// ~/.config/kotormodsync/telemetry.key (or AppData on Windows)
dev-signing-secret-not-for-production

// Code checks here second:
string configPath = Path.Combine(
    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
    "KOTORModSync", "telemetry.key");
if (File.Exists(configPath))
    return File.ReadAllText(configPath).Trim();
```

**Security:**
- ✅ Not in source code
- ✅ Not in git repo
- ✅ User-specific
- ⚠️ Use different secret than production

### Tier 3: None (Graceful Fail)
```csharp
if (string.IsNullOrEmpty(signingSecret))
{
    Log.Warning("Telemetry disabled: No signing secret found");
    return; // Don't initialize telemetry, continue running
}
```

**Security:**
- ✅ No crash
- ✅ No error spam
- ✅ Application fully functional
- ℹ️ Telemetry just doesn't work

## Implementation Checklist

### Server Side (bolabaden.org) ✅

- [x] Create authentication service (`kotormodsync-auth`)
- [x] Generate signing secret (64-char hex)
- [x] Store secret in Docker secret
- [x] Configure Traefik ForwardAuth middleware
- [x] Add rate limiting (10 req/s)
- [x] Deploy OTLP collector with auth
- [x] Add monitoring/alerts
- [x] Test endpoints

### Client Side (KOTORModSync)

- [ ] Add HMAC signing code (`TelemetryAuthenticator.cs`)
- [ ] Implement secret loading (3-tier priority)
- [ ] Add authentication headers to OTLP requests
- [ ] Add `.gitignore` entries for secrets
- [ ] Create template file (`EmbeddedSecrets.cs.example`)
- [ ] Update CI/CD to inject secret
- [ ] Add compile-time flag `OFFICIAL_BUILD`
- [ ] Test with/without secret
- [ ] Document for contributors

### GitHub Repository

- [ ] Add repository secret: `KOTORMODSYNC_SIGNING_SECRET`
- [ ] Update `.gitignore`:
  ```gitignore
  **/telemetry.key
  **/EmbeddedSecrets.cs
  ```
- [ ] Create `EmbeddedSecrets.cs.example`:
  ```csharp
  // Template - real secret injected during official builds
  namespace KOTORModSync.Telemetry {
      internal static class EmbeddedSecrets {
          internal const string TELEMETRY_SIGNING_KEY = "";
      }
  }
  ```
- [ ] Update `CONTRIBUTING.md`:
  ```markdown
  ## Telemetry Development
  
  Telemetry requires a signing secret. The application works without it,
  but won't send telemetry. To enable telemetry in development:
  
  1. Request dev secret from maintainers
  2. Create: `~/.config/kotormodsync/telemetry.key`
  3. Paste dev secret (NOT production secret!)
  ```

## Testing

### Test 1: Valid Signature
```bash
./scripts/test-kotormodsync-auth.sh valid
# Expected: HTTP 200 OK
```

### Test 2: Invalid Signature
```bash
./scripts/test-kotormodsync-auth.sh invalid
# Expected: HTTP 403 Forbidden
```

### Test 3: Missing Headers
```bash
curl -X POST https://otlp.bolabaden.org/v1/metrics
# Expected: HTTP 401 Unauthorized
```

### Test 4: Old Timestamp (Replay Attack)
```bash
OLD_TIMESTAMP=$(($(date +%s) - 400))  # 6 minutes ago
./scripts/test-kotormodsync-auth.sh replay "$OLD_TIMESTAMP"
# Expected: HTTP 401 Unauthorized (timestamp too old)
```

### Test 5: Rate Limiting
```bash
for i in {1..25}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://otlp.bolabaden.org/v1/metrics
done
# Expected: First 20 pass, last 5 get HTTP 429
```

## Secret Rotation Procedure

**When to rotate:**
- Every 90 days (scheduled)
- If secret is compromised
- Employee/contractor leaves team
- After security audit

**How to rotate:**

1. **Generate new secret:**
   ```bash
   openssl rand -hex 32 > /tmp/new_secret.txt
   ```

2. **Update server:**
   ```bash
   cp /tmp/new_secret.txt /home/ubuntu/my-media-stack/volumes/kotormodsync_signing_secret.txt
   docker compose restart kotormodsync-auth
   ```

3. **Update GitHub Actions:**
   - Go to: Settings → Secrets → Edit `KOTORMODSYNC_SIGNING_SECRET`
   - Paste new secret

4. **Publish new KOTORModSync release:**
   - Trigger release build
   - Old clients stop sending telemetry (expected)
   - Users update to new version

5. **Monitor:**
   ```bash
   docker compose logs -f kotormodsync-auth | grep AUTH_FAILED
   ```

## Monitoring & Alerts

### Key Metrics

```promql
# Authentication success rate
sum(rate(kotormodsync_auth_success[5m])) 
/ 
sum(rate(kotormodsync_auth_total[5m]))

# Failed authentication by reason
sum by (reason) (rate(kotormodsync_auth_failed[5m]))

# Telemetry volume
rate(kotormodsync_events_total[5m])
```

### Alerts

**High Failure Rate:**
```yaml
- alert: HighTelemetryAuthFailureRate
  expr: |
    sum(rate(kotormodsync_auth_failed[5m])) 
    / 
    sum(rate(kotormodsync_auth_total[5m])) > 0.2
  for: 10m
  annotations:
    summary: "20%+ of telemetry requests failing authentication"
```

**Auth Service Down:**
```yaml
- alert: TelemetryAuthServiceDown
  expr: up{job="kotormodsync-auth"} == 0
  for: 5m
  annotations:
    summary: "KOTORModSync auth service is down"
```

## Benefits Summary

✅ **Security:**
- No secrets in public repo
- Prevents abuse/spam
- Replay attack prevention
- Easy secret rotation

✅ **Developer Experience:**
- Builds work without secrets
- Clear documentation
- Automated CI/CD
- Graceful degradation

✅ **Operations:**
- Centralized authentication
- Audit logging
- Rate limiting
- Health monitoring

✅ **Scalability:**
- Lightweight auth service (< 50 MB RAM)
- High throughput (> 1000 req/s)
- Easy horizontal scaling
- No database required

## Documentation

- **Server Setup:** `docs/KOTORMODSYNC_TELEMETRY_SETUP.md`
- **Quick Start:** `docs/OTLP_QUICKSTART.md`
- **Client Integration:** `docs/KOTORMODSYNC_CLIENT_INTEGRATION.md`
- **This Document:** `docs/KOTORMODSYNC_SECURITY_SUMMARY.md`
- **Auth Service:** `projects/kotormodsync/telemetry-auth/README.md`

## Support

**Server Logs:**
```bash
docker compose logs -f kotormodsync-auth
docker compose logs -f otel-collector
```

**Service Status:**
```bash
docker compose ps | grep -E "auth|otel|prometheus"
```

**Test Endpoint:**
```bash
curl -I https://otlp.bolabaden.org
```

---

**Last Updated:** 2025-10-13
**Maintained By:** bolabaden.org Infrastructure Team

