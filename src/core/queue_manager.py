"""Smart Queue Manager - F61 Implementation.

Provides drag-and-drop queue management with priority reordering.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class QueueItemStatus(Enum):
    """Queue item status."""

    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    PAUSED = auto()


class QueuePriority(Enum):
    """Queue item priority."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class QueueItem:
    """A queue item."""

    id: str
    name: str
    task_type: str  # scan, sort, export, etc.
    status: QueueItemStatus = QueueItemStatus.PENDING
    priority: QueuePriority = QueuePriority.NORMAL
    position: int = 0
    progress: float = 0.0
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None


@dataclass
class QueueStats:
    """Queue statistics."""

    total_items: int = 0
    pending: int = 0
    in_progress: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0


class QueueManager:
    """Smart queue manager.

    Implements F61: Smart-Queue-Priority-Reordering

    Features:
    - Drag-and-drop reordering
    - Priority-based sorting
    - Pause/resume
    - Queue persistence
    """

    QUEUE_FILENAME = "queue_state.json"

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize queue manager.

        Args:
            cache_dir: Cache directory for persistence
        """
        self._cache_dir = Path(cache_dir) if cache_dir else Path("cache")
        self._items: Dict[str, QueueItem] = {}
        self._order: List[str] = []
        self._callbacks: List[Callable[[str, QueueItem], None]] = []
        self._is_processing = False
        self._current_item_id: Optional[str] = None

        self._load_state()

    def _load_state(self) -> None:
        """Load queue state from file."""
        state_file = self._cache_dir / self.QUEUE_FILENAME

        if not state_file.exists():
            return

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._order = data.get("order", [])

            for item_data in data.get("items", []):
                item = QueueItem(
                    id=item_data["id"],
                    name=item_data["name"],
                    task_type=item_data["task_type"],
                    status=QueueItemStatus[item_data.get("status", "PENDING")],
                    priority=QueuePriority[item_data.get("priority", "NORMAL")],
                    position=item_data.get("position", 0),
                    progress=item_data.get("progress", 0.0),
                    created_at=item_data.get("created_at", time.time()),
                    started_at=item_data.get("started_at"),
                    completed_at=item_data.get("completed_at"),
                    error_message=item_data.get("error_message", ""),
                    params=item_data.get("params", {}),
                )
                self._items[item.id] = item

            # Clean up order
            self._order = [id for id in self._order if id in self._items]

        except Exception:
            pass

    def _save_state(self) -> None:
        """Save queue state to file."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        state_file = self._cache_dir / self.QUEUE_FILENAME

        data = {
            "order": self._order,
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "task_type": item.task_type,
                    "status": item.status.name,
                    "priority": item.priority.name,
                    "position": item.position,
                    "progress": item.progress,
                    "created_at": item.created_at,
                    "started_at": item.started_at,
                    "completed_at": item.completed_at,
                    "error_message": item.error_message,
                    "params": item.params,
                }
                for item in self._items.values()
            ],
        }

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _notify_callbacks(self, event: str, item: QueueItem) -> None:
        """Notify registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(event, item)
            except Exception:
                pass

    def _update_positions(self) -> None:
        """Update item positions based on order."""
        for i, item_id in enumerate(self._order):
            if item_id in self._items:
                self._items[item_id].position = i

    def add(
        self,
        name: str,
        task_type: str,
        priority: QueuePriority = QueuePriority.NORMAL,
        params: Optional[Dict[str, Any]] = None,
    ) -> QueueItem:
        """Add item to queue.

        Args:
            name: Item name
            task_type: Type of task
            priority: Priority level
            params: Task parameters

        Returns:
            New QueueItem
        """
        item = QueueItem(
            id=str(uuid.uuid4()),
            name=name,
            task_type=task_type,
            priority=priority,
            params=params or {},
        )

        self._items[item.id] = item

        # Insert based on priority
        insert_pos = len(self._order)
        for i, existing_id in enumerate(self._order):
            existing = self._items.get(existing_id)
            if existing and existing.priority.value < priority.value:
                insert_pos = i
                break

        self._order.insert(insert_pos, item.id)
        self._update_positions()
        self._save_state()
        self._notify_callbacks("added", item)

        return item

    def remove(self, item_id: str) -> bool:
        """Remove item from queue.

        Args:
            item_id: Item ID

        Returns:
            True if removed
        """
        if item_id not in self._items:
            return False

        item = self._items[item_id]

        if item.status == QueueItemStatus.IN_PROGRESS:
            return False  # Can't remove running item

        del self._items[item_id]
        if item_id in self._order:
            self._order.remove(item_id)

        self._update_positions()
        self._save_state()
        self._notify_callbacks("removed", item)

        return True

    def move(self, item_id: str, new_position: int) -> bool:
        """Move item to new position (drag-and-drop).

        Args:
            item_id: Item ID
            new_position: New position index

        Returns:
            True if moved
        """
        if item_id not in self._items:
            return False

        if item_id not in self._order:
            return False

        current_pos = self._order.index(item_id)

        # Remove from current position
        self._order.remove(item_id)

        # Insert at new position
        new_position = max(0, min(new_position, len(self._order)))
        self._order.insert(new_position, item_id)

        self._update_positions()
        self._save_state()
        self._notify_callbacks("moved", self._items[item_id])

        return True

    def set_priority(self, item_id: str, priority: QueuePriority) -> bool:
        """Set item priority.

        Args:
            item_id: Item ID
            priority: New priority

        Returns:
            True if updated
        """
        if item_id not in self._items:
            return False

        item = self._items[item_id]
        item.priority = priority

        # Re-sort by priority
        self._order.sort(
            key=lambda id: (
                -self._items[id].priority.value,
                self._items[id].created_at,
            )
        )

        self._update_positions()
        self._save_state()
        self._notify_callbacks("priority_changed", item)

        return True

    def get(self, item_id: str) -> Optional[QueueItem]:
        """Get item by ID.

        Args:
            item_id: Item ID

        Returns:
            QueueItem or None
        """
        return self._items.get(item_id)

    def get_all(self) -> List[QueueItem]:
        """Get all items in order.

        Returns:
            List of QueueItems
        """
        return [self._items[id] for id in self._order if id in self._items]

    def get_pending(self) -> List[QueueItem]:
        """Get pending items.

        Returns:
            List of pending QueueItems
        """
        return [
            self._items[id]
            for id in self._order
            if id in self._items
            and self._items[id].status == QueueItemStatus.PENDING
        ]

    def get_next(self) -> Optional[QueueItem]:
        """Get next item to process.

        Returns:
            Next QueueItem or None
        """
        for item_id in self._order:
            item = self._items.get(item_id)
            if item and item.status == QueueItemStatus.PENDING:
                return item
        return None

    def start_item(self, item_id: str) -> bool:
        """Mark item as started.

        Args:
            item_id: Item ID

        Returns:
            True if started
        """
        if item_id not in self._items:
            return False

        item = self._items[item_id]
        item.status = QueueItemStatus.IN_PROGRESS
        item.started_at = time.time()
        item.progress = 0.0

        self._current_item_id = item_id
        self._is_processing = True
        self._save_state()
        self._notify_callbacks("started", item)

        return True

    def update_progress(self, item_id: str, progress: float) -> bool:
        """Update item progress.

        Args:
            item_id: Item ID
            progress: Progress (0.0 - 1.0)

        Returns:
            True if updated
        """
        if item_id not in self._items:
            return False

        item = self._items[item_id]
        item.progress = max(0.0, min(1.0, progress))

        self._notify_callbacks("progress", item)

        return True

    def complete_item(
        self, item_id: str, result: Optional[Any] = None
    ) -> bool:
        """Mark item as completed.

        Args:
            item_id: Item ID
            result: Optional result data

        Returns:
            True if completed
        """
        if item_id not in self._items:
            return False

        item = self._items[item_id]
        item.status = QueueItemStatus.COMPLETED
        item.completed_at = time.time()
        item.progress = 1.0
        item.result = result

        if self._current_item_id == item_id:
            self._current_item_id = None
            self._is_processing = False

        self._save_state()
        self._notify_callbacks("completed", item)

        return True

    def fail_item(self, item_id: str, error: str) -> bool:
        """Mark item as failed.

        Args:
            item_id: Item ID
            error: Error message

        Returns:
            True if updated
        """
        if item_id not in self._items:
            return False

        item = self._items[item_id]
        item.status = QueueItemStatus.FAILED
        item.completed_at = time.time()
        item.error_message = error

        if self._current_item_id == item_id:
            self._current_item_id = None
            self._is_processing = False

        self._save_state()
        self._notify_callbacks("failed", item)

        return True

    def cancel_item(self, item_id: str) -> bool:
        """Cancel item.

        Args:
            item_id: Item ID

        Returns:
            True if cancelled
        """
        if item_id not in self._items:
            return False

        item = self._items[item_id]

        if item.status == QueueItemStatus.COMPLETED:
            return False

        item.status = QueueItemStatus.CANCELLED
        item.completed_at = time.time()

        if self._current_item_id == item_id:
            self._current_item_id = None
            self._is_processing = False

        self._save_state()
        self._notify_callbacks("cancelled", item)

        return True

    def retry_item(self, item_id: str) -> bool:
        """Retry failed item.

        Args:
            item_id: Item ID

        Returns:
            True if queued for retry
        """
        if item_id not in self._items:
            return False

        item = self._items[item_id]

        if item.status not in (QueueItemStatus.FAILED, QueueItemStatus.CANCELLED):
            return False

        item.status = QueueItemStatus.PENDING
        item.started_at = None
        item.completed_at = None
        item.progress = 0.0
        item.error_message = ""
        item.result = None

        self._save_state()
        self._notify_callbacks("retry", item)

        return True

    def clear_completed(self) -> int:
        """Clear completed items.

        Returns:
            Number of items cleared
        """
        to_remove = [
            id
            for id, item in self._items.items()
            if item.status
            in (
                QueueItemStatus.COMPLETED,
                QueueItemStatus.CANCELLED,
            )
        ]

        for item_id in to_remove:
            del self._items[item_id]
            if item_id in self._order:
                self._order.remove(item_id)

        self._update_positions()
        self._save_state()

        return len(to_remove)

    def get_stats(self) -> QueueStats:
        """Get queue statistics.

        Returns:
            QueueStats
        """
        stats = QueueStats(total_items=len(self._items))

        for item in self._items.values():
            if item.status == QueueItemStatus.PENDING:
                stats.pending += 1
            elif item.status == QueueItemStatus.IN_PROGRESS:
                stats.in_progress += 1
            elif item.status == QueueItemStatus.COMPLETED:
                stats.completed += 1
            elif item.status == QueueItemStatus.FAILED:
                stats.failed += 1
            elif item.status == QueueItemStatus.CANCELLED:
                stats.cancelled += 1

        return stats

    @property
    def is_processing(self) -> bool:
        """Check if queue is processing."""
        return self._is_processing

    @property
    def current_item(self) -> Optional[QueueItem]:
        """Get current processing item."""
        if self._current_item_id:
            return self._items.get(self._current_item_id)
        return None

    def register_callback(
        self, callback: Callable[[str, QueueItem], None]
    ) -> None:
        """Register event callback.

        Args:
            callback: Callback(event, item)
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(
        self, callback: Callable[[str, QueueItem], None]
    ) -> None:
        """Unregister callback.

        Args:
            callback: Callback to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
