# 🚀 Cursor Result Listener Deployment Checklist

## 📋 Pre-Deployment Validation

### Code Quality
- [ ] Run full test suite: `pytest tests/tools/test_cursor_result_listener.py -v`
- [ ] Verify test coverage ≥90%: `pytest --cov=tools.cursor_result_listener --cov-report=html`
- [ ] Check memory leak tests pass: `pytest tests/tools/test_cursor_result_listener.py -k test_memory_cleanup`
- [ ] Validate concurrent processing: `pytest tests/tools/test_cursor_result_listener.py -k test_concurrent_file_processing`
- [ ] Run system resilience tests: `pytest tests/tools/test_cursor_result_listener.py -k test_system_resilience`

### Configuration
- [ ] Verify all required settings in production config:
  ```yaml
  cursor:
    poll_interval: 1.0  # Production recommended value
    metrics_port: 9090  # Standard Prometheus port
    pending_dir: "/var/dream/cursor/pending"
    processing_dir: "/var/dream/cursor/processing"
    archive_dir: "/var/dream/cursor/archive"
    error_dir: "/var/dream/cursor/error"
    feedback_dir: "/var/dream/cursor/feedback"
    context_file: "/var/dream/cursor/context.json"
    log_file: "/var/log/dream/cursor.log"
  ```

### System Requirements
- [ ] Verify Python 3.8+ installed
- [ ] Check disk space for log directories (recommend 20GB+)
- [ ] Validate file permissions on all directories
- [ ] Confirm Prometheus endpoint accessible
- [ ] Test network connectivity to required services

## 🔄 Deployment Steps

### 1. Backup
- [ ] Create backup of existing context file
- [ ] Archive current logs
- [ ] Snapshot current metrics

### 2. System Preparation
- [ ] Create required directories with correct permissions:
  ```bash
  mkdir -p /var/dream/cursor/{pending,processing,archive,error,feedback}
  chown -R dream:dream /var/dream/cursor
  chmod 755 /var/dream/cursor
  ```
- [ ] Configure log rotation:
  ```bash
  /var/log/dream/cursor.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 dream dream
  }
  ```

### 3. Service Deployment
- [ ] Stop existing service: `systemctl stop cursor-listener`
- [ ] Deploy new code
- [ ] Apply new configuration
- [ ] Create/update systemd service:
  ```ini
  [Unit]
  Description=Dream OS Cursor Result Listener
  After=network.target

  [Service]
  Type=simple
  User=dream
  Group=dream
  WorkingDirectory=/opt/dream
  ExecStart=/usr/bin/python3 -m tools.cursor_result_listener
  Restart=always
  RestartSec=5

  [Install]
  WantedBy=multi-user.target
  ```
- [ ] Start service: `systemctl start cursor-listener`

### 4. Monitoring Setup
- [ ] Configure Prometheus targets
- [ ] Set up Grafana dashboards:
  - Queue sizes
  - Processing duration
  - Error rates
  - Memory usage
- [ ] Configure alerts for:
  - High error rate (>5% in 5m)
  - Queue growth (>1000 pending)
  - Memory usage (>85%)
  - Processing delays (>30s)

## ✅ Post-Deployment Validation

### Immediate Checks
- [ ] Verify service running: `systemctl status cursor-listener`
- [ ] Check logs for startup errors: `journalctl -u cursor-listener -n 50`
- [ ] Confirm metrics endpoint responding: `curl localhost:9090/-/healthy`
- [ ] Test file processing with sample prompt
- [ ] Verify feedback generation

### 24-Hour Monitoring
- [ ] Monitor error rates
- [ ] Check memory usage stability
- [ ] Verify file cleanup working
- [ ] Validate metrics collection
- [ ] Review processing latency

## 🔄 Rollback Plan

### Triggers
- Error rate exceeds 10% in 15 minutes
- Memory usage above 90%
- Processing queue grows beyond 5000 files
- Critical service errors in logs

### Steps
1. Stop new service: `systemctl stop cursor-listener`
2. Restore previous version
3. Restore configuration backup
4. Start previous version: `systemctl start cursor-listener`
5. Verify system stability
6. Process any backlogged files

## 📝 Documentation

- [ ] Update system architecture diagrams
- [ ] Document new metrics/alerts
- [ ] Update runbooks
- [ ] Record deployment in change log
- [ ] Update API documentation if changed

## 🏁 Final Sign-off

- [ ] Development team approval
- [ ] Operations team approval
- [ ] Security review complete
- [ ] Performance baseline established
- [ ] Monitoring confirmed working 