import boto3
from boto3.dynamodb.conditions import Attr
from storage.base import StorageInterface

class DynamoDBStorage(StorageInterface):
    def __init__(self, table_name="Predictions"):
        self.table = boto3.resource("dynamodb").Table(table_name)

    async def save_prediction(self, uid, original_image, predicted_image):
        self.table.put_item(Item={
            "uid": uid,
            "original_image": original_image,
            "predicted_image": predicted_image,
            "detection_objects": []
        })

    async def save_detection(self, prediction_uid, label, score, box):
        self.table.update_item(
            Key={"uid": prediction_uid},
            UpdateExpression="SET detection_objects = list_append(detection_objects, :new_item)",
            ExpressionAttributeValues={
                ":new_item": [{"label": label, "score": score, "box": box}]
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
        resp = self.table.scan(
            FilterExpression=Attr("detection_objects").exists()
        )
        results = []
        for item in resp["Items"]:
            for det in item["detection_objects"]:
                if det["score"] >= min_score:
                    results.append({"uid": item["uid"], "timestamp": item.get("timestamp")})
                    break
        return results

    async def get_prediction_image_path(self, uid):
        resp = self.table.get_item(Key={"uid": uid})
        item = resp.get("Item")
        return item.get("predicted_image") if item else None
