"""Asynchronous Task Queue"""
import asyncio
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Callable, Any
from enum import Enum

from api.config import TASK_TTL_SECONDS, MAX_QUEUE_SIZE


class TaskStatus(str, Enum):
    """Task status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Task:
    """Task object"""
    
    def __init__(self, task_id: str, coro: Callable):
        self.task_id = task_id
        self.coro = coro
        self.status = TaskStatus.PENDING
        self.progress = 0.0
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Path] = None
        self.error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        data = {
            "task_id": self.task_id,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() + 'Z',
            "started_at": self.started_at.isoformat() + 'Z' if self.started_at else None,
            "completed_at": self.completed_at.isoformat() + 'Z' if self.completed_at else None,
        }
        
        if self.status == TaskStatus.COMPLETED and self.result:
            data["download_url"] = f"/api/v1/ocr/task/{self.task_id}/download"
        
        if self.status == TaskStatus.FAILED and self.error:
            data["error"] = self.error
        
        return data


class TaskQueue:
    """Async task queue manager"""
    
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        self.tasks: Dict[str, Task] = {}
        self.worker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
    
    async def start_worker(self):
        """Start background worker"""
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._worker())
    
    async def stop_worker(self):
        """Stop background worker"""
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
    
    async def submit_task(self, coro: Callable) -> str:
        """
        Submit a task to the queue.
        
        Args:
            coro: Coroutine to execute
            
        Returns:
            Task ID
            
        Raises:
            RuntimeError: If queue is full
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Create task
        task = Task(task_id, coro)
        
        async with self._lock:
            self.tasks[task_id] = task
        
        # Add to queue
        try:
            await asyncio.wait_for(
                self.queue.put(task),
                timeout=1.0
            )
        except asyncio.TimeoutError:
            async with self._lock:
                del self.tasks[task_id]
            raise RuntimeError("Task queue is full, please try again later")
        
        return task_id
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        async with self._lock:
            return self.tasks.get(task_id)
    
    async def get_task_result(self, task_id: str) -> Optional[Path]:
        """Get task result (output directory path)"""
        task = await self.get_task(task_id)
        if task and task.status == TaskStatus.COMPLETED:
            return task.result
        return None
    
    async def cleanup_old_tasks(self):
        """Clean up old completed/failed tasks"""
        async with self._lock:
            cutoff_time = datetime.utcnow() - timedelta(seconds=TASK_TTL_SECONDS)
            
            to_delete = []
            for task_id, task in self.tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    if task.completed_at and task.completed_at < cutoff_time:
                        to_delete.append(task_id)
            
            for task_id in to_delete:
                # Clean up result files
                task = self.tasks[task_id]
                if task.result and task.result.exists():
                    try:
                        import shutil
                        shutil.rmtree(task.result)
                    except:
                        pass
                
                del self.tasks[task_id]
    
    async def _worker(self):
        """Background worker to process tasks"""
        while True:
            try:
                # Get next task
                task = await self.queue.get()
                
                # Update status
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.utcnow()
                
                try:
                    # Execute task
                    result = await task.coro
                    
                    # Mark as completed
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.utcnow()
                    task.result = result
                    task.progress = 1.0
                    
                except Exception as e:
                    # Mark as failed
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.utcnow()
                    task.error = {
                        "message": str(e),
                        "type": type(e).__name__
                    }
                
                finally:
                    self.queue.task_done()
                
                # Periodic cleanup
                if len(self.tasks) > 100:  # Cleanup threshold
                    await self.cleanup_old_tasks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker error: {e}")
                await asyncio.sleep(1)


# Global task queue instance
_task_queue = TaskQueue()


async def get_task_queue() -> TaskQueue:
    """Get global task queue instance"""
    if _task_queue.worker_task is None or _task_queue.worker_task.done():
        await _task_queue.start_worker()
    return _task_queue
