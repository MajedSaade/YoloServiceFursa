#!/bin/bash

# Replace `yolo.service` if it's named differently
sudo cp yolo.service /etc/systemd/system/

# Reload systemd and restart the YOLO FastAPI service
sudo systemctl daemon-reload
sudo systemctl restart yolo.service
sudo systemctl enable yolo.service

# Check if the service is active
if ! systemctl is-active --quiet yolo.service; then
  echo "❌ yolo.service is not running."
  sudo systemctl status yolo.service --no-pager
  exit 1
fi
