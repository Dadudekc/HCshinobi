from typing import Dict, List, Set
from .task_queue import Task, TaskStatus

class DependencyResolver:
    def __init__(self):
        self._dependency_graph: Dict[str, Set[str]] = {}
    
    def add_dependencies(self, task_id: str, dependencies: List[str]) -> None:
        if task_id not in self._dependency_graph:
            self._dependency_graph[task_id] = set()
        self._dependency_graph[task_id].update(dependencies)
    
    def remove_dependencies(self, task_id: str, dependencies: List[str]) -> None:
        if task_id in self._dependency_graph:
            self._dependency_graph[task_id].difference_update(dependencies)
    
    def get_dependencies(self, task_id: str) -> Set[str]:
        return self._dependency_graph.get(task_id, set())
    
    def get_dependents(self, task_id: str) -> Set[str]:
        dependents = set()
        for dependent, deps in self._dependency_graph.items():
            if task_id in deps:
                dependents.add(dependent)
        return dependents
    
    def is_task_ready(self, task: Task, tasks: Dict[str, Task]) -> bool:
        if not task.dependencies:
            return True
        
        for dep_id in task.dependencies:
            if dep_id not in tasks:
                return False
            
            dep_task = tasks[dep_id]
            if dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    def get_ready_tasks(self, tasks: Dict[str, Task]) -> List[Task]:
        ready_tasks = []
        for task in tasks.values():
            if task.status == TaskStatus.PENDING and self.is_task_ready(task, tasks):
                ready_tasks.append(task)
        return ready_tasks
    
    def has_cycle(self) -> bool:
        visited = set()
        path = set()
        
        def visit(vertex):
            if vertex in path:
                return True
            if vertex in visited:
                return False
            
            path.add(vertex)
            visited.add(vertex)
            
            for neighbor in self._dependency_graph.get(vertex, set()):
                if visit(neighbor):
                    return True
            
            path.remove(vertex)
            return False
        
        for vertex in self._dependency_graph:
            if visit(vertex):
                return True
        
        return False
    
    def get_task_order(self) -> List[str]:
        if self.has_cycle():
            raise ValueError("Dependency graph contains cycles")
        
        visited = set()
        order = []
        
        def visit(vertex):
            if vertex in visited:
                return
            visited.add(vertex)
            
            for neighbor in self._dependency_graph.get(vertex, set()):
                visit(neighbor)
            
            order.append(vertex)
        
        for vertex in self._dependency_graph:
            visit(vertex)
        
        return list(reversed(order)) 