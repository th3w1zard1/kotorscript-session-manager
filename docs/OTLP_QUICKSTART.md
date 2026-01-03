# OTLP Collector Quick Start

## 5-Minute Setup

### 1. Deploy the Stack

```bash
cd /home/ubuntu/my-media-stack

# Start the metrics stack with OTLP collector
docker compose up -d otel-collector prometheus

# Wait 30 seconds for services to start
sleep 30

# Check status
docker compose ps | grep -E "otel-collector|prometheus"
```

### 2. Verify OTLP Collector is Running

```bash
# Check health
docker compose exec otel-collector wget -qO- http://localhost:8888/metrics | head -20

# Check logs for errors
docker compose logs --tail=50 otel-collector
```

Expected output: Prometheus-formatted metrics with no errors in logs.

### 3. Test External Access

```bash
# Test OTLP HTTP endpoint (from external machine or server)
curl -X POST https://otlp.bolabaden.org/v1/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "resourceMetrics": [
      {
        "resource": {
          "attributes": [
            {"key": "service.name", "value": {"stringValue": "test-service"}}
          ]
        },
        "scopeMetrics": [
          {
            "metrics": [
              {
                "name": "test_metric",
                "unit": "1",
                "gauge": {
                  "dataPoints": [
                    {
                      "asInt": "42",
                      "timeUnixNano": "'$(date +%s)000000000'"
                    }
                  ]
                }
              }
            ]
          }
        ]
      }
    ]
  }'
```

Expected response: HTTP 200 OK

### 4. Verify Prometheus Integration

```bash
# Check if Prometheus received remote write
docker compose logs prometheus | grep -i "remote write" | tail -5

# Query for OTLP collector metrics in Prometheus
curl -s 'http://localhost:9090/api/v1/query?query=up{job="otel-collector"}' | jq

# Should show: "value": ["timestamp", "1"]
```

### 5. Test Rate Limiting (Optional)

```bash
# Send 25 rapid requests (should trigger rate limit after 20)
for i in {1..25}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://otlp.bolabaden.org/v1/metrics \
    -H "Content-Type: application/json" \
    -d '{"resourceMetrics":[]}'
done

# Expected: First 20 return 200/400, last 5 return 429 (rate limited)
```

## Quick Reference

### Endpoints

| Endpoint | Purpose | Access |
|----------|---------|--------|
| `https://otlp.bolabaden.org` | OTLP HTTP ingestion | Public |
| `https://prometheus.bolabaden.org` | Prometheus UI | Auth required |
| `https://grafana.bolabaden.org` | Grafana dashboards | Auth required |
| `http://localhost:8888/metrics` | OTLP collector metrics | Internal only |

### Common Commands

```bash
# View OTLP collector logs
docker compose logs -f otel-collector

# Restart OTLP collector
docker compose restart otel-collector

# Check resource usage
docker stats otel-collector

# View Prometheus config
docker compose exec prometheus cat /etc/prometheus/prometheus.yml | grep -A 10 "otel-collector"

# Force config reload (no restart needed)
docker compose exec prometheus wget -qO- --post-data='' http://localhost:9090/-/reload
```

### Prometheus Queries for KOTORModSync Metrics

Once clients start sending data:

```promql
# All KOTORModSync metrics
{__name__=~"kotormodsync.*"}

# Event types
sum by (event_type) (kotormodsync_events_total)

# Platform distribution
count by (platform) (kotormodsync_events_total)

# Active sessions (last 5 minutes)
count(count by (session_id) (kotormodsync_events_total[5m]))
```

## Troubleshooting

### Issue: Collector not starting

```bash
# Check detailed logs
docker compose logs otel-collector

# Common fixes:
docker compose down otel-collector
docker compose up -d otel-collector
```

### Issue: Can't reach otlp.bolabaden.org

```bash
# Check Traefik routing
docker compose logs traefik | grep -i otlp

# Verify DNS
dig otlp.bolabaden.org

# Test from inside network
docker compose exec otel-collector wget -qO- http://localhost:4318/v1/metrics
```

### Issue: Metrics not showing in Prometheus

```bash
# 1. Verify remote write is enabled
docker compose exec prometheus ps aux | grep "enable-remote-write-receiver"

# 2. Check for errors in Prometheus logs
docker compose logs prometheus | grep -i error

# 3. Verify OTLP collector can reach Prometheus
docker compose exec otel-collector wget -qO- http://prometheus:9090/-/healthy
```

## Success Indicators

✅ **Collector is healthy:**
```bash
docker compose ps otel-collector
# Status: Up (healthy)
```

✅ **External endpoint accessible:**
```bash
curl -I https://otlp.bolabaden.org
# HTTP/2 200 or 405 (method not allowed for GET)
```

✅ **Prometheus shows collector as up:**
```bash
curl -s 'http://localhost:9090/api/v1/query?query=up{job="otel-collector"}' | grep '"1"'
# Should return a match
```

✅ **No errors in logs:**
```bash
docker compose logs --tail=100 otel-collector | grep -i error
# Should return no critical errors
```

## What's Next?

1. ✅ Configure KOTORModSync to send telemetry to `https://otlp.bolabaden.org`
2. ✅ Create Grafana dashboards for visualization
3. ✅ Set up Alertmanager notifications for collector downtime
4. ✅ Monitor resource usage over first 24 hours

## Need Help?

- **Logs:** `docker compose logs -f otel-collector prometheus`
- **Status:** `docker compose ps`
- **Config:** `cat compose/docker-compose.metrics.yml | grep -A 50 otel-collector:`
- **Full Guide:** See `docs/KOTORMODSYNC_TELEMETRY_SETUP.md`

