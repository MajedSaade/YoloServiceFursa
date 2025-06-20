import boto3
import os
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Attr
from storage.base import StorageInterface

class DynamoDBStorage(StorageInterface):
    def __init__(self, table_name=None):
        if table_name is None:
            table_name = os.getenv("DYNAMODB_TABLE_NAME", "Predictions")
        self.table = boto3.resource("dynamodb").Table(table_name)

    def _convert_floats_to_decimal(self, obj):
        """Convert float values to Decimal for DynamoDB compatibility"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_floats_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimal(v) for v in obj]
        return obj

    async def save_prediction(self, uid, original_image, predicted_image):
        self.table.put_item(Item={
            "uid": uid,
            "timestamp": datetime.utcnow().isoformat(),
            "original_image": original_image,
            "predicted_image": predicted_image,
            "detection_objects": []
        })

    async def save_detection(self, prediction_uid, label, score, box):
        # Convert score to Decimal
        decimal_score = Decimal(str(score))
        
        self.table.update_item(
            Key={"uid": prediction_uid},
            UpdateExpression="SET detection_objects = list_append(detection_objects, :new_item)",
            ExpressionAttributeValues={
                ":new_item": [{"label": label, "score": decimal_score, "box": box}]
            }
        )

    async def get_prediction(self, uid):
        resp = self.table.get_item(Key={"uid": uid})
        return resp.get("Item")

    async def get_predictions_by_label(self, label):
        resp = self.table.scan(
            FilterExpression=Attr("detection_objects").contains({"label": label})
        )
        return [{"uid": item["uid"], "timestamp": item.get("timestamp")} for item in resp["Items"]]

    async def get_predictions_by_score(self, min_score):
        # Convert min_score to Decimal for comparison
        decimal_min_score = Decimal(str(min_score))
        
        resp = self.table.scan(
            FilterExpression=Attr("detection_objects").exists()
        )
        results = []
        for item in resp["Items"]:
            for det in item["detection_objects"]:
                if det["score"] >= decimal_min_score:
                    results.append({"uid": item["uid"], "timestamp": item.get("timestamp")})
                    break
        return results

    async def get_prediction_image_path(self, uid):
        resp = self.table.get_item(Key={"uid": uid})
        item = resp.get("Item")
        return item.get("predicted_image") if item else None
