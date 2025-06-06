#!/bin/bash

set -e  # Exit on any error

echo "Deploying YOLO FastAPI service..."

# Replace `yolo.service` if it's named differently
echo "Setting up yolo.service..."
sudo cp yolo.service /etc/systemd/system/

# Reload systemd and restart the YOLO FastAPI service
sudo systemctl daemon-reload
sudo systemctl restart yolo.service
sudo systemctl enable yolo.service

# Check if the YOLO service is active
if ! systemctl is-active --quiet yolo.service; then
  echo "❌ yolo.service is not running."
  sudo systemctl status yolo.service --no-pager
  exit 1
fi

echo "✅ yolo.service is running successfully."

# --- OpenTelemetry Collector installation and setup ---

echo "Installing OpenTelemetry Collector..."
wget https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.127.0/otelcol_0.127.0_linux_amd64.deb
sudo dpkg -i otelcol_0.127.0_linux_amd64.deb

echo "Configuring OpenTelemetry Collector..."
sudo tee /etc/otelcol/config.yaml > /dev/null << EOL
receivers:
  hostmetrics:
    collection_interval: 15s
    scrapers:
      cpu:
      memory:
      disk:
      filesystem:
      load:
      network:
      processes:

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"

service:
  pipelines:
    metrics:
      receivers: [hostmetrics]
      exporters: [prometheus]
EOL

echo "Creating otelcol systemd service..."
sudo tee /etc/systemd/system/otelcol.service > /dev/null << EOL
[Unit]
Description=OpenTelemetry Collector
After=network-online.target

[Service]
ExecStart=/usr/bin/otelcol --config=/etc/otelcol/config.yaml
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOL

echo "Enabling and restarting otelcol service..."
sudo systemctl daemon-reload
sudo systemctl enable otelcol
sudo systemctl restart otelcol

# Check if the otelcol service is active
if ! systemctl is-active --quiet otelcol.service; then
  echo "❌ otelcol.service is not running."
  sudo systemctl status otelcol.service --no-pager
  exit 1
fi

echo "✅ otelcol.service is running successfully."
