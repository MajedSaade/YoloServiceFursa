from abc import ABC, abstractmethod

class StorageInterface(ABC):
    @abstractmethod
    async def save_prediction(self, uid: str, original_image: str, predicted_image: str):
        pass

    @abstractmethod
    async def save_detection(self, prediction_uid: str, label: str, score: float, box: str):
        pass

    @abstractmethod
    async def get_prediction(self, uid: str):
        pass

    @abstractmethod
    async def get_predictions_by_label(self, label: str):
        pass

    @abstractmethod
    async def get_predictions_by_score(self, min_score: float):
        pass

    @abstractmethod
    async def get_prediction_image_path(self, uid: str):
        pass
