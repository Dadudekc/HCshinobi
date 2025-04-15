#!/bin/bash

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Create necessary directories
mkdir -p grafana/provisioning/datasources
mkdir -p grafana/provisioning/dashboards
mkdir -p grafana_dashboards

# Copy dashboard to provisioning directory
cp grafana_dashboards/cursor_metrics_dashboard.json grafana_dashboards/

# Create Grafana datasource provisioning
cat > grafana/provisioning/datasources/prometheus.yml <<EOL
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOL

# Create Grafana dashboard provisioning
cat > grafana/provisioning/dashboards/dream_os.yml <<EOL
apiVersion: 1

providers:
  - name: 'Dream.OS'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: true
    editable: false
    options:
      path: /var/lib/grafana/dashboards
EOL

# Start the monitoring stack
docker-compose up -d

# Wait for services to be ready
echo "Waiting for Prometheus to be ready..."
until curl -s http://localhost:9090/-/ready > /dev/null; do
    sleep 1
done

echo "Waiting for Grafana to be ready..."
until curl -s http://localhost:3000/api/health > /dev/null; do
    sleep 1
done

echo "Monitoring stack is ready!"
echo "Prometheus UI: http://localhost:9090"
echo "Grafana UI: http://localhost:3000"
echo "Default Grafana credentials: admin/admin" 