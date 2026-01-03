# KOTORModSync Telemetry Setup Guide

## Overview

This guide explains the OpenTelemetry (OTLP) collector setup for receiving telemetry data from KOTORModSync clients at `otlp.bolabaden.org`.

## Architecture

```
KOTORModSync Clients (behind NATs/firewalls)
            |
            | PUSH telemetry via HTTPS
            v
    otlp.bolabaden.org (Traefik)
            |
            v
    OpenTelemetry Collector (Docker)
            |
            | Remote Write API
            v
    Prometheus (existing at prometheus.bolabaden.org)
            |
            v
    Grafana (existing at grafana.bolabaden.org)
```

## What Was Added

### 1. OpenTelemetry Collector Service

**Location:** `compose/docker-compose.metrics.yml`

The OTLP collector service:
- **Container:** `otel-collector`
- **Image:** `docker.io/otel/opentelemetry-collector-contrib:latest`
- **Exposed Endpoints:**
  - `https://otlp.bolabaden.org` (port 4318) - OTLP HTTP endpoint
  - OTLP gRPC (port 4317) - Alternative protocol
  - Metrics endpoint (port 8888) - Collector's own metrics

**Features:**
- ✅ Receives OTLP telemetry (traces & metrics) from clients
- ✅ Batches data for efficient processing
- ✅ Exports metrics to Prometheus via remote write API
- ✅ Rate limiting: 10 requests/second per IP (burst: 20)
- ✅ Health checks enabled
- ✅ Resource limits: 2GB RAM, 1 CPU
- ✅ Automatic restart on failure

### 2. Prometheus Configuration

**Changes Made:**
- ✅ Enabled remote write receiver: `--web.enable-remote-write-receiver`
- ✅ Added scrape job for OTLP collector metrics
- ✅ Added blackbox monitoring for `otlp.bolabaden.org`
- ✅ Added alert rule for OTLP collector downtime

### 3. OTLP Collector Configuration

**Location:** Inline config in `docker-compose.metrics.yml` (lines 4450-4501)

**Receivers:**
- OTLP HTTP (port 4318)
- OTLP gRPC (port 4317)

**Processors:**
- Batch processor (10s timeout, 1024 samples per batch)
- Resource processor (adds `service.namespace: kotormodsync`)

**Exporters:**
- Prometheus remote write → `http://prometheus:9090/api/v1/write`
- Logging (for debugging)

### 4. Traefik Configuration

**Labels Added:**
- HTTP router: `otlp.$DOMAIN` → port 4318
- gRPC router: `otlp.$DOMAIN` → port 4317
- Rate limiting middleware: 10 req/s per IP, burst 20
- TLS termination handled by Traefik

### 5. Monitoring & Alerts

**Prometheus Scrapes:**
- OTLP collector metrics every 15 seconds
- Collector health status monitoring

**Uptime Kuma:**
- HTTP health check every 60 seconds at `https://otlp.bolabaden.org`

**Alertmanager Rule:**
- Alert `OtelCollectorDown` if collector is down for >5 minutes
- Severity: Warning

**Homepage Dashboard:**
- Group: Infrastructure
- Icon: OpenTelemetry
- Link: `https://otlp.$DOMAIN`

## Deployment Steps

### 1. Deploy the Stack

```bash
cd /home/ubuntu/my-media-stack

# Pull the new image
docker compose pull otel-collector

# Start/restart the metrics stack
docker compose --profile metrics up -d

# Verify OTLP collector is running
docker compose ps otel-collector
docker compose logs -f otel-collector
```

### 2. Verify Endpoints

**Test OTLP HTTP endpoint:**
```bash
curl -X POST https://otlp.bolabaden.org/v1/metrics \
  -H "Content-Type: application/json" \
  -d '{"resourceMetrics":[]}'

# Expected: HTTP 200 or 400 (both indicate service is running)
```

**Test OTLP collector metrics:**
```bash
curl http://localhost:8888/metrics

# Expected: Prometheus metrics output
```

**Test Prometheus remote write is accepting data:**
```bash
docker compose logs prometheus | grep "remote write"
```

### 3. Verify in Grafana

1. Open Grafana: `https://grafana.bolabaden.org`
2. Navigate to Explore
3. Select Prometheus data source
4. Query: `up{job="otel-collector"}`
5. Expected: Value should be `1` (collector is up)

### 4. Test KOTORModSync Integration

Once KOTORModSync clients start sending data, verify metrics are being received:

```bash
# Check for KOTORModSync metrics in Prometheus
curl -G 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=kotormodsync_events_total'

# Or query all metrics with kotormodsync prefix
curl -G 'http://localhost:9090/api/v1/label/__name__/values' | grep kotormodsync
```

Expected metrics from KOTORModSync:
- `kotormodsync_events_total`
- `kotormodsync_errors_total`
- `kotormodsync_operation_duration_milliseconds`
- `kotormodsync_mods_installed_total`
- `kotormodsync_mods_validated_total`
- `kotormodsync_downloads_total`
- `kotormodsync_download_size_bytes`

All metrics include labels:
- `user_id` (anonymous GUID)
- `session_id` (changes each run)
- `platform` (Windows/Linux/OSX)

## Troubleshooting

### OTLP Collector Not Starting

```bash
# Check logs
docker compose logs otel-collector

# Common issues:
# 1. Port conflict on 4318/4317
# 2. Config syntax error
# 3. Prometheus not reachable
```

### Prometheus Not Receiving Data

```bash
# Check remote write is enabled
docker compose exec prometheus wget -qO- http://localhost:9090/api/v1/status/config | grep enable-remote-write-receiver

# Check OTLP collector can reach Prometheus
docker compose exec otel-collector wget -qO- http://prometheus:9090/-/healthy

# Check Prometheus logs for remote write errors
docker compose logs prometheus | grep -i "remote write"
```

### Clients Getting Connection Errors

```bash
# Test from outside
curl -v https://otlp.bolabaden.org/v1/metrics

# Check Traefik routing
docker compose logs traefik | grep otlp

# Verify DNS
dig otlp.bolabaden.org

# Check SSL certificate
openssl s_client -connect otlp.bolabaden.org:443 -servername otlp.bolabaden.org
```

### Rate Limiting Issues

If legitimate clients are being rate-limited:

1. Check current rate limit in `docker-compose.metrics.yml` (line ~4695):
   ```yaml
   traefik.http.middlewares.otlp-ratelimit.ratelimit.average: 10
   traefik.http.middlewares.otlp-ratelimit.ratelimit.burst: 20
   ```

2. Adjust as needed:
   - `average`: Requests per second per IP
   - `burst`: Maximum burst size

3. Restart to apply:
   ```bash
   docker compose up -d otel-collector
   ```

## Configuration Reference

### Environment Variables

No additional environment variables required. The OTLP collector uses existing infrastructure variables:

- `$DOMAIN` - Your domain (e.g., `bolabaden.org`)
- `$TS_HOSTNAME` - Tailscale hostname
- `$CONFIG_PATH` - Config volume path (default: `./volumes`)

### Ports

| Port | Protocol | Purpose | Exposed |
|------|----------|---------|---------|
| 4318 | HTTP | OTLP HTTP receiver | Via Traefik (443) |
| 4317 | gRPC | OTLP gRPC receiver | Via Traefik (443) |
| 8888 | HTTP | Collector metrics | Internal only |
| 9090 | HTTP | Prometheus | Via Traefik (443) |

### Networks

The OTLP collector is connected to:
- `backend` - For communication with Prometheus
- `publicnet` - For external access via Traefik

## Monitoring

### Grafana Dashboards

Create dashboards to visualize:

1. **KOTORModSync Usage Metrics:**
   - Total events by type
   - Error rates
   - Operation duration percentiles
   - Mod installation trends
   - Download statistics by platform

2. **OTLP Collector Health:**
   - Ingestion rate
   - Export rate to Prometheus
   - Queue depth
   - Batch sizes
   - Dropped spans/metrics

Example queries:

```promql
# Event rate by type
rate(kotormodsync_events_total[5m])

# Error percentage
rate(kotormodsync_errors_total[5m]) / rate(kotormodsync_events_total[5m]) * 100

# P95 operation duration
histogram_quantile(0.95, rate(kotormodsync_operation_duration_milliseconds_bucket[5m]))

# Active users (last hour)
count(count by (user_id) (kotormodsync_events_total[1h]))

# Collector metrics processed per second
rate(otelcol_receiver_accepted_metric_points[5m])
```

### Uptime Monitoring

Uptime Kuma automatically monitors:
- `https://otlp.bolabaden.org` - HTTP 200 check every 60s

Alert is triggered if collector is unreachable.

## Security Considerations

### Current Setup

- ✅ HTTPS/TLS encryption via Traefik
- ✅ Rate limiting (10 req/s per IP)
- ✅ No authentication required (by design)
- ✅ Metrics contain anonymous user IDs only

### Optional Enhancements

If you want to add authentication:

1. **Add API Key to OTLP Collector:**

   Update `otel-collector-config.yaml` in `docker-compose.metrics.yml`:
   ```yaml
   receivers:
     otlp:
       protocols:
         http:
           endpoint: 0.0.0.0:4318
           auth:
             authenticator: headers
   
   extensions:
     headers_setter:
       headers:
         - key: authorization
           value: Bearer YOUR_SECRET_TOKEN
   ```

2. **Configure Traefik Auth:**

   Add BasicAuth or ForwardAuth middleware to the OTLP router labels.

3. **IP Whitelisting:**

   If clients have static IPs, use Traefik's IP whitelist middleware.

## Performance Tuning

### High Load Optimization

If receiving >1000 metrics/second:

1. **Increase batch size** (lines 4462-4463):
   ```yaml
   batch:
     timeout: 5s
     send_batch_size: 2048
   ```

2. **Increase resource limits** (lines 4716-4718):
   ```yaml
   cpus: 2
   mem_limit: 4G
   ```

3. **Enable horizontal scaling** (add multiple replicas):
   ```bash
   docker compose up -d --scale otel-collector=3
   ```

### Low Resource Mode

If running on constrained hardware:

1. **Reduce batch timeout:**
   ```yaml
   batch:
     timeout: 30s  # Send less frequently
   ```

2. **Disable verbose logging:**
   ```yaml
   logging:
     verbosity: normal
   ```

## Backup & Recovery

### Configuration Backup

The OTLP collector config is stored inline in `docker-compose.metrics.yml`. Back up this file regularly:

```bash
cp compose/docker-compose.metrics.yml compose/docker-compose.metrics.yml.backup
```

### Data Persistence

- Prometheus stores metrics in `${CONFIG_PATH}/prometheus/data`
- OTLP collector is stateless (no persistent data)
- Backup Prometheus data directory for historical metrics

## Support

For issues with:

- **OTLP Collector:** Check logs with `docker compose logs otel-collector`
- **Prometheus:** Check logs with `docker compose logs prometheus`
- **KOTORModSync Client:** Check application logs for telemetry errors

## Summary

You now have a fully functional OTLP endpoint at `https://otlp.bolabaden.org` that:

1. ✅ Receives telemetry from KOTORModSync clients worldwide
2. ✅ Exports metrics to your existing Prometheus instance
3. ✅ Includes rate limiting and monitoring
4. ✅ Integrates with your existing observability stack
5. ✅ Provides alerts for downtime
6. ✅ Supports both HTTP and gRPC protocols

**Next Steps:**
1. Deploy the stack with `docker compose up -d`
2. Verify endpoints are accessible
3. Test with KOTORModSync client
4. Create Grafana dashboards for visualization
5. Monitor for any issues in the first 24 hours

