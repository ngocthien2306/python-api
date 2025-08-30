from abc import ABC, abstractmethod
from typing import Dict, Any
from bson import ObjectId
from datetime import datetime

class BaseModel(ABC):
    def __init__(self):
        self._id: ObjectId = None
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        result = self.__dict__.copy()
        if self._id is not None:
            result['_id'] = self._id
        else:
            result.pop('_id', None) 
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        instance = cls()
        for key, value in data.items():
            setattr(instance, key, value)
        return instance
