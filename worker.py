import os
import threading
import time
import json
import urllib.request
import boto3
import requests
from ultralytics import YOLO
from storage.sqlite import SQLiteStorage
from storage.dynamodb import DynamoDBStorage

# Config
SQS_URL = os.getenv("SQS_URL")
S3_BUCKET = os.getenv("S3_BUCKET")
POLYBOT_CALLBACK = os.getenv("POLYBOT_CALLBACK_URL")

# Storage backend
storage = SQLiteStorage()  # or DynamoDBStorage()

model = YOLO("yolov8n.pt")

def poll_sqs():
    sqs = boto3.client("sqs")
    while True:
        resp = sqs.receive_message(QueueUrl=SQS_URL, MaxNumberOfMessages=1, WaitTimeSeconds=10)
        for msg in resp.get("Messages", []):
            body = json.loads(msg["Body"])
            handle_message(body)
            sqs.delete_message(QueueUrl=SQS_URL, ReceiptHandle=msg["ReceiptHandle"])
        time.sleep(2)

def handle_message(body):
    pid = body["prediction_id"]
    image_url = body["image_url"]
    chat_id = body["chat_id"]
    local = f"temp/{pid}.jpg"
    os.makedirs("temp", exist_ok=True)
    urllib.request.urlretrieve(image_url, local)

    results = model(local, device="cpu")
    annotated = results[0].plot()
    result_data = {
        "original_image": image_url,
        "predicted_image": annotated.tolist() if hasattr(annotated, "tolist") else image_url,
        "detections": [
            {"label": model.names[int(b.cls)], "confidence": float(b.conf), "bbox": b.xyxy.tolist()}
            for b in results[0].boxes
        ]
    }
    requests.post(f"{POLYBOT_CALLBACK}/{pid}", json=result_data)

threading.Thread(target=poll_sqs, daemon=True).start()
