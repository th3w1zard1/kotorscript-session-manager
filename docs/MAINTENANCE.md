# Media Stack Maintenance Guide

This document describes the automated maintenance system that prevents disk space issues and keeps your media stack running smoothly.

## 🎯 Problem This Solves

Docker-based media stacks can accumulate disk space through:
- Docker overlay2 layers from stopped containers
- Application caches (Stremio, Open-WebUI, Prometheus, etc.)
- Unrotated container logs
- Metrics data (Prometheus WAL, VictoriaMetrics)
- System logs and temporary files

This maintenance system automatically cleans up these resources to prevent disk exhaustion.

## 🛠️ What's Included

### 1. Docker Daemon Configuration
**Location:** `configs/docker-daemon.json`

Configures Docker-wide log rotation:
- **max-size:** 10MB per log file
- **max-file:** Keep 3 rotated files
- **compress:** Compress rotated logs
- **live-restore:** Containers survive Docker daemon restarts

**Installation:**
```bash
./scripts/setup-docker-daemon.sh
```

### 2. Automated Maintenance Script
**Location:** `scripts/docker-maintenance.sh`

Runs comprehensive cleanup:
- ✅ Removes stopped containers (>7 days old)
- ✅ Removes unused images (>30 days old)
- ✅ Removes unused volumes (without `keep` label)
- ✅ Removes unused networks
- ✅ Removes build cache (>7 days old)
- ✅ Truncates large container logs (>100MB → 50MB)
- ✅ Cleans application caches (Prometheus, Stremio, VictoriaMetrics, Open-WebUI)
- ✅ Cleans system caches (APT, NPM, Python UV)
- ✅ Rotates system logs (keep 30 days)
- ✅ Cleans temporary files (>7 days old)

**Manual run:**
```bash
sudo /home/ubuntu/my-media-stack/scripts/docker-maintenance.sh
```

### 3. Automated Cron Jobs
**Location:** `scripts/setup-crontabs.sh`

Schedules automatic maintenance:
- **Weekly full cleanup:** Sundays at 2:00 AM
- **Daily light cleanup:** Every day at 3:00 AM (containers + logs)
- **Daily disk monitoring:** Every day at 4:00 AM

**Installation:**
```bash
./scripts/setup-crontabs.sh
```

**View installed cron jobs:**
```bash
crontab -l
```

### 4. Docker Compose Maintenance Overlay
**Location:** `compose/docker-compose.maintenance.yml`

Adds logging and resource limits to all services:
- Logging configuration (10MB max, 3 files, compressed)
- Memory limits for each service
- Health checks where applicable

**Usage:**
```bash
docker compose -f docker-compose.yml -f compose/docker-compose.maintenance.yml up -d
```

Or add to your `docker-compose.yml`:
```yaml
include:
  - compose/docker-compose.maintenance.yml
```

### 5. Environment Configuration
**Location:** `.env.maintenance`

Recommended settings for cache/retention limits:
- Prometheus: 15 days retention, 10GB max size
- VictoriaMetrics: 60 days retention, 40% memory limit
- Loki: 30 days retention
- Resource limits for all services

**Apply settings:**
```bash
# Review first!
cat .env.maintenance

# Merge into your .env (careful of duplicates)
# Manually copy relevant lines from .env.maintenance to .env
```

### 6. Emergency Cleanup Script
**Location:** `scripts/emergency-cleanup.sh`

For critical low-disk situations. Aggressively removes:
- All Docker resources (stopped containers, unused images, volumes)
- Application caches
- System logs (keep 7 days)
- Temporary files

**Usage:**
```bash
./scripts/emergency-cleanup.sh
# Will prompt for confirmation
```

### 7. Cloud-Init Bootstrap
**Location:** `scripts/cloud-init-maintenance.sh`

Automated setup for new VPS instances:
- Installs Docker & Docker Compose
- Clones repository
- Installs maintenance system
- Configures monitoring
- Sets up helpful aliases

**Usage in cloud-init:**
```yaml
#cloud-config
runcmd:
  - curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/my-media-stack/main/scripts/cloud-init-maintenance.sh | bash
```

**Manual run:**
```bash
sudo bash scripts/cloud-init-maintenance.sh
```

## 📊 Monitoring

### Check Disk Usage
```bash
# Overall system
df -h /

# Docker-specific
docker system df

# Detailed breakdown
ncdu /

# Application data
du -sh /opt/docker/data/*
```

### View Maintenance Logs
```bash
# Maintenance script logs
tail -f /var/log/docker-maintenance.log

# Disk usage alerts
tail -f /var/log/disk-usage.log

# System logs
journalctl -u docker -f
```

### Check Service Status
```bash
# Docker containers
docker ps -a

# Cron jobs
crontab -l

# Systemd timer (if using cloud-init)
systemctl status media-stack-monitor.timer
```

## 🔧 Customization

### Adjust Cleanup Schedule
Edit crontab:
```bash
crontab -e
```

Example schedules:
```bash
# Every 3 days at 2 AM
0 2 */3 * * /path/to/docker-maintenance.sh

# Twice weekly (Sunday and Wednesday)
0 2 * * 0,3 /path/to/docker-maintenance.sh
```

### Adjust Retention Periods
Edit `scripts/docker-maintenance.sh`:
```bash
# Change these values:
CONTAINER_RETENTION_HOURS=168    # 7 days
IMAGE_RETENTION_HOURS=720        # 30 days
BUILD_CACHE_RETENTION_HOURS=168  # 7 days
LOG_RETENTION_DAYS=30
```

### Exclude Volumes from Cleanup
Add a label to volumes you want to keep:
```yaml
volumes:
  important-data:
    labels:
      - "keep=true"
```

### Service-Specific Limits
Edit `.env` with values from `.env.maintenance`:
```bash
# Prometheus
PROMETHEUS_RETENTION_TIME=15d
PROMETHEUS_RETENTION_SIZE=10GB

# VictoriaMetrics
VICTORIAMETRICS_RETENTION_PERIOD=60d
```

## 🚨 Troubleshooting

### Disk Still Filling Up?

1. **Check what's using space:**
   ```bash
   sudo ncdu /
   # Focus on /var/lib/docker and /opt/docker/data
   ```

2. **Identify largest Docker directories:**
   ```bash
   du -h -d 3 /var/lib/docker/overlay2 | sort -hr | head -20
   ```

3. **Check for runaway containers:**
   ```bash
   docker stats --no-stream
   docker ps -a
   ```

4. **Find large logs:**
   ```bash
   find /var/lib/docker/containers -name "*.log" -size +100M -exec ls -lh {} \;
   ```

5. **Run aggressive cleanup:**
   ```bash
   ./scripts/emergency-cleanup.sh
   ```

### Cron Jobs Not Running?

1. **Check cron service:**
   ```bash
   systemctl status cron
   ```

2. **Check cron logs:**
   ```bash
   grep CRON /var/log/syslog | tail -20
   ```

3. **Verify script is executable:**
   ```bash
   ls -la /home/ubuntu/my-media-stack/scripts/docker-maintenance.sh
   chmod +x /home/ubuntu/my-media-stack/scripts/docker-maintenance.sh
   ```

4. **Test script manually:**
   ```bash
   sudo /home/ubuntu/my-media-stack/scripts/docker-maintenance.sh
   ```

### Docker Daemon Config Not Applied?

1. **Validate JSON:**
   ```bash
   sudo python3 -m json.tool /etc/docker/daemon.json
   ```

2. **Reload Docker:**
   ```bash
   sudo systemctl reload docker
   # or
   sudo systemctl restart docker
   ```

3. **Check for conflicting configs:**
   ```bash
   ls -la /etc/docker/daemon.json*
   ```

## 📦 Complete Installation

Run the all-in-one installer:

```bash
cd /home/ubuntu/my-media-stack
./scripts/install-maintenance-system.sh
```

This will:
1. ✅ Configure Docker daemon with log rotation
2. ✅ Install cron jobs for automated cleanup
3. ✅ Setup log rotation for maintenance logs
4. ✅ Create emergency cleanup script
5. ✅ Display next steps

## 🔄 Updates

To update the maintenance system:

```bash
cd /home/ubuntu/my-media-stack
git pull
./scripts/install-maintenance-system.sh
```

## 📚 Additional Resources

- [Docker System Prune](https://docs.docker.com/config/pruning/)
- [Docker Logging Configuration](https://docs.docker.com/config/containers/logging/configure/)
- [Prometheus Storage](https://prometheus.io/docs/prometheus/latest/storage/)
- [VictoriaMetrics Configuration](https://docs.victoriametrics.com/)

## 🆘 Getting Help

If you encounter issues:

1. Check logs: `/var/log/docker-maintenance.log`
2. Check disk usage: `df -h / && docker system df`
3. Review cron jobs: `crontab -l`
4. Check Docker daemon: `journalctl -u docker`

## 📝 License

Same as parent project.

