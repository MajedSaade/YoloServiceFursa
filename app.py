from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from ultralytics import YOLO
from PIL import Image
import os, uuid, shutil, asyncio
import torch
from prometheus_fastapi_instrumentator import Instrumentator

# Disable GPU usage
torch.cuda.is_available = lambda: False

# Load appropriate storage backend
storage_type = os.getenv("STORAGE_TYPE", "sqlite")
if storage_type == "dynamodb":
    from storage.dynamodb import DynamoDBStorage
    storage = DynamoDBStorage()
else:
    from storage.sqlite import SQLiteStorage
    storage = SQLiteStorage()

# Setup directories and app
UPLOAD_DIR = "uploads/original"
PREDICTED_DIR = "uploads/predicted"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PREDICTED_DIR, exist_ok=True)

model = YOLO("yolov8n.pt")
app = FastAPI()
Instrumentator().instrument(app).expose(app)

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1]
    uid = str(uuid.uuid4())
    original_path = os.path.join(UPLOAD_DIR, uid + ext)
    predicted_path = os.path.join(PREDICTED_DIR, uid + ext)

    with open(original_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    results = model(original_path, device="cpu")
    annotated_frame = results[0].plot()
    Image.fromarray(annotated_frame).save(predicted_path)

    await storage.save_prediction(uid, original_path, predicted_path)

    for box in results[0].boxes:
        label = model.names[int(box.cls)]
        score = float(box.conf)
        bbox = str(box.xyxy.tolist())
        await storage.save_detection(uid, label, score, bbox)

    return {
        "prediction_uid": uid,
        "detection_count": len(results[0].boxes),
        "labels": [model.names[int(b.cls)] for b in results[0].boxes]
    }

@app.get("/prediction/{uid}")
async def get_prediction_by_uid(uid: str):
    data = await storage.get_prediction(uid)
    if not data:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return data

@app.get("/predictions/label/{label}")
async def get_predictions_by_label(label: str):
    return await storage.get_predictions_by_label(label)

@app.get("/predictions/score/{min_score}")
async def get_predictions_by_score(min_score: float):
    return await storage.get_predictions_by_score(min_score)

@app.get("/image/{type}/{filename}")
def get_image(type: str, filename: str):
    if type not in ["original", "predicted"]:
        raise HTTPException(status_code=400, detail="Invalid image type")
    path = os.path.join("uploads", type, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)

@app.get("/prediction/{uid}/image")
async def get_prediction_image(uid: str, request: Request):
    accept = request.headers.get("accept", "")
    path = await storage.get_prediction_image_path(uid)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")

    if "image/png" in accept:
        return FileResponse(path, media_type="image/png")
    elif "image/jpeg" in accept or "image/jpg" in accept:
        return FileResponse(path, media_type="image/jpeg")
    raise HTTPException(status_code=406, detail="Client does not accept an image format")

@app.post("/predictions/{uid}")
async def receive_prediction(uid: str, request: Request):
    data = await request.json()
    await storage.save_prediction(uid, data["original_image"], data["predicted_image"])
    for det in data["detections"]:
        await storage.save_detection(uid, det["label"], det["confidence"], str(det["bbox"]))
    return {"status": "ok"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
