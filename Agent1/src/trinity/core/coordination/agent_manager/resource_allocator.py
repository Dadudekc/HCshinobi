from typing import Dict, List, Optional, Set
from pydantic import BaseModel

class Resource(BaseModel):
    resource_id: str
    resource_type: str
    capacity: float
    allocated: float = 0.0
    agent_id: Optional[str] = None

class ResourceAllocator:
    def __init__(self):
        self._resources: Dict[str, Resource] = {}
        self._agent_resources: Dict[str, Set[str]] = {}
    
    def register_resource(self, resource_id: str, resource_type: str, capacity: float) -> Resource:
        if resource_id in self._resources:
            raise ValueError(f"Resource {resource_id} already registered")
        
        resource = Resource(
            resource_id=resource_id,
            resource_type=resource_type,
            capacity=capacity
        )
        self._resources[resource_id] = resource
        return resource
    
    def allocate_resource(self, agent_id: str, resource_id: str, amount: float) -> bool:
        if resource_id not in self._resources:
            raise ValueError(f"Resource {resource_id} not found")
        
        resource = self._resources[resource_id]
        if resource.allocated + amount > resource.capacity:
            return False
        
        resource.allocated += amount
        resource.agent_id = agent_id
        
        if agent_id not in self._agent_resources:
            self._agent_resources[agent_id] = set()
        self._agent_resources[agent_id].add(resource_id)
        
        return True
    
    def release_resource(self, agent_id: str, resource_id: str, amount: float) -> None:
        if resource_id not in self._resources:
            raise ValueError(f"Resource {resource_id} not found")
        
        resource = self._resources[resource_id]
        if resource.agent_id != agent_id:
            raise ValueError(f"Resource {resource_id} not allocated to agent {agent_id}")
        
        resource.allocated = max(0, resource.allocated - amount)
        if resource.allocated == 0:
            resource.agent_id = None
            self._agent_resources[agent_id].remove(resource_id)
    
    def get_available_resources(self, resource_type: Optional[str] = None) -> List[Resource]:
        return [
            resource for resource in self._resources.values()
            if (resource_type is None or resource.resource_type == resource_type)
            and resource.allocated < resource.capacity
        ]
    
    def get_agent_resources(self, agent_id: str) -> List[Resource]:
        if agent_id not in self._agent_resources:
            return []
        
        return [
            self._resources[resource_id]
            for resource_id in self._agent_resources[agent_id]
        ]
    
    def get_resource_utilization(self, resource_id: str) -> float:
        if resource_id not in self._resources:
            raise ValueError(f"Resource {resource_id} not found")
        
        resource = self._resources[resource_id]
        return resource.allocated / resource.capacity if resource.capacity > 0 else 0.0 