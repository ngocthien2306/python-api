from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, TypeVar, Generic
from bson import ObjectId

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    def __init__(self, database):
        self.database = database
        self.collection = None
    
    @abstractmethod
    def get_collection_name(self) -> str:
        pass
    
    def get_collection(self):
        if self.collection is None:
            self.collection = self.database[self.get_collection_name()]
        return self.collection
    
    def create(self, document: Dict[str, Any]) -> str:
        result = self.get_collection().insert_one(document)
        return str(result.inserted_id)
    
    def find_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self.get_collection().find_one({"_id": ObjectId(doc_id)})
    
    def find(self, query: Dict[str, Any], limit: int = None) -> List[Dict[str, Any]]:
        cursor = self.get_collection().find(query)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)
    
    def update(self, doc_id: str, update_data: Dict[str, Any]) -> bool:
        result = self.get_collection().update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    def delete(self, doc_id: str) -> bool:
        result = self.get_collection().delete_one({"_id": ObjectId(doc_id)})
        return result.deleted_count > 0
    
    def count(self, query: Dict[str, Any]) -> int:
        return self.get_collection().count_documents(query)
    
    def find_by_query(self, query: Dict[str, Any], limit: int = None, 
                     sort: List[tuple] = None) -> List[Dict[str, Any]]:
        """
        Enhanced query method with sorting support
        sort parameter: List of tuples like [("field", 1)] for ascending, [("field", -1)] for descending
        """
        cursor = self.get_collection().find(query)
        
        if sort:
            cursor = cursor.sort(sort)
        
        if limit:
            cursor = cursor.limit(limit)
            
        return list(cursor)
