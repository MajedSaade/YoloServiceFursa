#!/bin/bash

set -e  # Exit on any error

echo "Deploying YOLO FastAPI service..."

# Optional: clean pip and apt cache to free disk space
echo "Cleaning pip and apt cache..."
pip cache purge || true
sudo apt-get clean

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip wget

# Setup yolo.service
echo "Setting up yolo.service..."
sudo cp yolo.service /etc/systemd/system/

# Reload systemd and enable yolo.service
sudo systemctl daemon-reload
sudo systemctl enable yolo.service

# Setup Python virtual environment
echo "Setting up Python virtual environment..."
cd ~/YoloServiceFursa
if [ ! -d ".venv" ]; then
    echo "Creating new virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment and installing requirements..."
. .venv/bin/activate
pip install --upgrade pip

# STEP 1 — install CPU-only torch first
echo "Installing CPU-only torch..."
pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision

# STEP 2 — install the rest of the requirements
echo "Installing remaining requirements..."
pip install -r requirements.txt

# Restart yolo.service
echo "Restarting yolo.service..."
sudo systemctl restart yolo.service

# Check if yolo.service is active
if ! systemctl is-active --quiet yolo.service; then
  echo "❌ yolo.service is not running."
  sudo systemctl status yolo.service --no-pager
  exit 1
fi
echo "✅ yolo.service is running successfully."

# --- Clean up old otelcol .deb files to save disk space ---
echo "Cleaning up old otelcol .deb files..."
rm -f ~/otelcol_0.127.0_linux_amd64.deb*

# --- Install OpenTelemetry Collector ---
echo "Installing OpenTelemetry Collector..."
wget https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.127.0/otelcol_0.127.0_linux_amd64.deb
sudo dpkg -i otelcol_0.127.0_linux_amd64.deb

# --- Configure OpenTelemetry Collector ---
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

# Create otelcol systemd service (optional override in case needed)
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

# Enable and restart otelcol
echo "Enabling and restarting otelcol service..."
sudo systemctl daemon-reload
sudo systemctl enable otelcol
sudo systemctl restart otelcol

# Check if otelcol.service is active
if ! systemctl is-active --quiet otelcol.service; then
  echo "❌ otelcol.service is not running."
  sudo systemctl status otelcol.service --no-pager
  exit 1
fi
echo "✅ otelcol.service is running successfully."
