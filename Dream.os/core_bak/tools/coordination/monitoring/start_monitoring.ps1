# Change to script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Create necessary directories
New-Item -ItemType Directory -Force -Path grafana/provisioning/datasources
New-Item -ItemType Directory -Force -Path grafana/provisioning/dashboards
New-Item -ItemType Directory -Force -Path grafana_dashboards

# Copy dashboard to provisioning directory
Copy-Item -Force grafana_dashboards/cursor_metrics_dashboard.json grafana_dashboards/

# Create Grafana datasource provisioning
@"
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
"@ | Out-File -FilePath grafana/provisioning/datasources/prometheus.yml -Encoding UTF8

# Create Grafana dashboard provisioning
@"
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
"@ | Out-File -FilePath grafana/provisioning/dashboards/dream_os.yml -Encoding UTF8

# Start the monitoring stack
docker-compose up -d

# Wait for services to be ready
Write-Host "Waiting for Prometheus to be ready..."
do {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9090/-/ready" -UseBasicParsing -ErrorAction SilentlyContinue
        $ready = $response.StatusCode -eq 200
    } catch {
        $ready = $false
    }
} while (-not $ready)

Write-Host "Waiting for Grafana to be ready..."
do {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -UseBasicParsing -ErrorAction SilentlyContinue
        $ready = $response.StatusCode -eq 200
    } catch {
        $ready = $false
    }
} while (-not $ready)

Write-Host "Monitoring stack is ready!"
Write-Host "Prometheus UI: http://localhost:9090"
Write-Host "Grafana UI: http://localhost:3000"
Write-Host "Default Grafana credentials: admin/admin" 