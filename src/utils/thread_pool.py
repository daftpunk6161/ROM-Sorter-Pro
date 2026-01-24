#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rome Sorter Pro - advanced thread pool Phase 1 Implementation: Desktop optimization This module offers improved thread pool implementation for the Parallel processing of tasks with progressive error treatment, Resource management and adaptive performance optimization."""

import os
import threading
import queue
import time
import logging
import traceback
from typing import Dict, List, Tuple, Optional, Callable, Any

# Logging einrichten
logger = logging.getLogger(__name__)

class Task:
    """Represents a task that is to be carried out by the thread pool."""

    def __init__(self, func: Callable, args: tuple = (), kwargs: dict = {},
                task_id: Optional[str] = None, priority: int = 0):
        """Initialized A New Task. Args: Func: The Function to Be Carried Out Args: Position Argents for the Function Kwargs: Key Virtues for the Function Task_ID: Optional ID for the Task (is generated automatically, if not specific) Priority: Priority of the Task (Higher Numbers = Higher Priority)"""
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.task_id = task_id or f"task_{id(self)}"
        self.priority = priority
        self.creation_time = time.time()
        self.start_time = None
        self.end_time = None
        self.result = None
        self.error = None
        self.status = "pending"  # pending, running, completed, failed, cancelled

    def __lt__(self, other):
        """Comparison for priority taue - higher priority first."""
        if self.priority != other.priority:
            return self.priority > other.priority  # Higher numbers = higher priority
        return self.creation_time < other.creation_time  # With the same priority: fifo

    def execute(self):
        """Performs the task and records the result or error."""
        self.start_time = time.time()
        self.status = "running"

        try:
            self.result = self.func(*self.args, **self.kwargs)
            self.status = "completed"
        except Exception as e:
            self.error = e
            self.status = "failed"
            logger.error(f"Task {self.task_id} failed: {str(e)}")
            logger.debug(traceback.format_exc())

        self.end_time = time.time()
        return self

class AdaptiveThreadPool:
    """A thread pool with adaptive performance optimization, priority support and extended monitoring function."""

    def __init__(self, min_workers: int = 2, max_workers: int = None,
                name_prefix: str = "worker", daemon: bool = True):
        """Initialized the thread pool. Args: Min_Workers: Minimal number of worker threads MAX_WORKERS: Maximum number of worker threads (None for CPU number * 2) Name_Prefix: Prefix for thread names Daemon: Whether the threads should run as Daemon threads"""
        self.min_workers = min_workers
        self.max_workers = max_workers or (os.cpu_count() or 4) * 2
        self.name_prefix = name_prefix
        self.daemon = daemon

        # Task Queues and Worker Management
        self.task_queue = queue.PriorityQueue()
        self.workers = []
        self.active_workers = 0
        self.total_tasks_submitted = 0
        self.total_tasks_completed = 0
        self.total_tasks_failed = 0

        # Callbacks
        self.on_task_start = lambda task: None  # Callback: (task: Task) -> None
        self.on_task_complete = lambda task, result=None: None  # Callback: (task: Task, result) -> None
        self.on_task_error = lambda task, error=None: None  # Callback: (task: Task, error: Exception) -> None

        # Status and synchronization
        self.running = False
        self._lock = threading.RLock()
        self._worker_event = threading.Event()
        self._shutdown_event = threading.Event()

        # Performance monitoring and adaptation
        self.performance_metrics = {
            'avg_task_time': 0.0,
            'avg_queue_time': 0.0,
            'throughput': 0.0,
            'last_adjustment_time': 0.0
        }
        self.adjustment_interval = 10.0  # Sekunden zwischen Anpassungen

        # Thread for performance monitoring and worker adjustment
        self.monitor_thread = None

    def start(self):
        """Startet den Thread-Pool."""
        with self._lock:
            if self.running:
                return

            self.running = True
            self._shutdown_event.clear()

            # Initialize the worker threads
            for _ in range(self.min_workers):
                self._add_worker()

            # Start the surveillance thread
            self.monitor_thread = threading.Thread(
                target=self._monitor_performance,
                name=f"{self.name_prefix}_monitor",
                daemon=True
            )
            self.monitor_thread.start()

            logger.info(f"AdaptiveThreadPool gestartet mit {self.min_workers} Workern")

    def shutdown(self, wait: bool = True):
        """Drives down the thread pool. Args: Wait: Whether all tasks should be served"""
        with self._lock:
            if not self.running:
                return

            self.running = False
            self._shutdown_event.set()
            self._worker_event.set()  # Weckt alle wartenden Worker auf

        if wait:
            # Warte auf Beendigung aller Worker
            for worker in self.workers:
                if worker.is_alive():
                    worker.join()

        logger.info("AdaptiveThreadPool heruntergefahren")

    def submit(self, func: Callable, *args, **kwargs) -> str:
        """Sends a Task for Execution. Args: Func: The Function to Be Carried Out *Args: Position Argents for the Function ** Kwargs: Key Virtues for the Functional Key Wort Argents: - Task_ID: Optional ID for the Task - Priority (Higher Numbers = Higher Priority) Return: The ID of the Task"""
        # Spezielle Kwargs extrahieren
        task_id = kwargs.pop('task_id', None)
        priority = kwargs.pop('priority', 0)

        task = Task(func, args, kwargs, task_id, priority)

        with self._lock:
            self.total_tasks_submitted += 1
            self.task_queue.put(task)
            self._worker_event.set()  # Weckt einen wartenden Worker auf

        # Check whether we need more worker
        self._check_worker_count()

        return task.task_id

    def _add_worker(self):
        """Add a new worker thread to the pool."""
        with self._lock:
            if len(self.workers) >= self.max_workers:
                return False

            worker_id = len(self.workers) + 1
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"{self.name_prefix}_{worker_id}",
                daemon=self.daemon
            )
            self.workers.append(worker)
            worker.start()

            logger.debug(f"Worker {worker.name} gestartet")
            return True

    def _worker_loop(self):
        """Main loop for worker threads."""
        while self.running and not self._shutdown_event.is_set():
            try:
                # Try to get a task
                try:
                    # Wait for a Task for a short time
                    task = self.task_queue.get(timeout=0.1)
                except queue.Empty:
                    # No task available, check whether we should end
                    if self._shutdown_event.is_set():
                        break

                    # Wait for a signal or timeout
                    self._worker_event.wait(1.0)
                    self._worker_event.clear()
                    continue

                # Found task, lead them out
                with self._lock:
                    self.active_workers += 1

                if self.on_task_start:
                    try:
                        self.on_task_start(task)
                    except Exception as e:
                        logger.error(f"Fehler im on_task_start-Callback: {e}")

                # Perform the task
                task.execute()

                # Aktualisiere Statistiken
                with self._lock:
                    self.active_workers -= 1

                    if task.status == "completed":
                        self.total_tasks_completed += 1

                        # Aktualisiere Performance-Metriken
                        task_time = task.end_time - task.start_time
                        queue_time = task.start_time - task.creation_time

                        # Exponentieller gleitender Durchschnitt
                        alpha = 0.1  # Gewichtungsfaktor
                        self.performance_metrics['avg_task_time'] = (
                            (1 - alpha) * self.performance_metrics['avg_task_time'] +
                            alpha * task_time
                        )
                        self.performance_metrics['avg_queue_time'] = (
                            (1 - alpha) * self.performance_metrics['avg_queue_time'] +
                            alpha * queue_time
                        )

                        if self.on_task_complete:
                            try:
                                self.on_task_complete(task)
                            except Exception as e:
                                logger.error(f"Fehler im on_task_complete-Callback: {e}")

                    elif task.status == "failed":
                        self.total_tasks_failed += 1

                        if self.on_task_error:
                            try:
                                self.on_task_error(task, task.error)
                            except Exception as e:
                                logger.error(f"Fehler im on_task_error-Callback: {e}")

                # Mark the task as done
                self.task_queue.task_done()

            except Exception as e:
                logger.error(f"Unerwarteter Fehler im Worker-Thread: {e}")
                logger.debug(traceback.format_exc())

    def _check_worker_count(self):
        """Checks if the number of workers needs to be adjusted."""
        now = time.time()

        # Do not adapt too often
        if now - self.performance_metrics['last_adjustment_time'] < self.adjustment_interval:
            return

        with self._lock:
            queue_size = self.task_queue.qsize()
            current_workers = len(self.workers)
            active_workers = self.active_workers

            # When the cue grows and we have active workers
            # Let's add more workers
            if queue_size > current_workers * 2 and active_workers >= current_workers * 0.8:
                workers_to_add = min(
                    queue_size // 4,  # A Maximum of 1/4 of the Queue Size
                    self.max_workers - current_workers  # But no more than maximum allowed
                )

                for _ in range(workers_to_add):
                    if not self._add_worker():
                        break

                if workers_to_add > 0:
                    logger.info(f"{workers_to_add} Worker hinzugefügt (jetzt {len(self.workers)})")

            # Update time of the last adjustment
            self.performance_metrics['last_adjustment_time'] = now

    def _monitor_performance(self):
        """Monitors the performance and adapts the number of workers."""
        while self.running and not self._shutdown_event.is_set():
            try:
                # Sleep for an interval
                time.sleep(self.adjustment_interval)

                with self._lock:
                    if not self.running or self._shutdown_event.is_set():
                        break

                    # Berechne Durchsatz (Tasks pro Sekunde)
                    now = time.time()
                    elapsed = now - self.performance_metrics['last_adjustment_time']
                    if elapsed > 0:
                        current_throughput = (
                            self.total_tasks_completed / elapsed
                            if self.total_tasks_completed > 0 else 0
                        )

                        # Aktualisiere den durchschnittlichen Durchsatz
                        alpha = 0.2  # Gewichtungsfaktor
                        self.performance_metrics['throughput'] = (
                            (1 - alpha) * self.performance_metrics['throughput'] +
                            alpha * current_throughput
                        )

                    # Check whether we have to adjust the number of workers
                    self._check_worker_count()

                    # Update the time of the last adaptation
                    self.performance_metrics['last_adjustment_time'] = now

                    # Log Performance-Metriken
                    logger.debug(
                        f"Performance: Worker={len(self.workers)}, "
                        f"Aktiv={self.active_workers}, "
                        f"Queue={self.task_queue.qsize()}, "
                        f"Avg Task Time={self.performance_metrics['avg_task_time']:.3f}s, "
                        f"Throughput={self.performance_metrics['throughput']:.2f} tasks/s"
                    )

            except Exception as e:
                logger.error(f"Fehler im Performance-Monitoring-Thread: {e}")
                logger.debug(traceback.format_exc())

    def wait_completion(self):
        """Wartet, bis alle Aufgaben abgeschlossen sind."""
        self.task_queue.join()

    @property
    def stats(self) -> Dict[str, Any]:
        """Gives back current statistics of the thread pool."""
        with self._lock:
            return {
                'workers': len(self.workers),
                'active_workers': self.active_workers,
                'queue_size': self.task_queue.qsize(),
                'submitted': self.total_tasks_submitted,
                'completed': self.total_tasks_completed,
                'failed': self.total_tasks_failed,
                'avg_task_time': self.performance_metrics['avg_task_time'],
                'avg_queue_time': self.performance_metrics['avg_queue_time'],
                'throughput': self.performance_metrics['throughput']
            }

class BatchProcessor:
    """
    Processes batches of tasks with an AdaptiveThreadPool
    and provides enhanced functions for batch processing.
    """

    def __init__(self, min_workers: int = 2, max_workers: int = None):
        """Initialized the batch processor. Args: Min_Workers: Minimal number of worker threads Max_Workers: Maximum number of worker threads"""
        self.thread_pool = AdaptiveThreadPool(
            min_workers=min_workers,
            max_workers=max_workers,
            name_prefix="batch_worker"
        )

        # Batch-Status
        self.batches = {}
        self.batch_counter = 0
        self.current_batch = None

        # Callbacks
        self.on_batch_start = lambda batch_id, batch: None
        self.on_batch_complete = lambda batch_id, batch: None
        self.on_batch_progress = lambda batch_id, batch, progress: None

        # Status and synchronization
        self._lock = threading.RLock()

    def start(self):
        """Startet den Thread-Pool."""
        self.thread_pool.start()

        # Callbacks verbinden
        self.thread_pool.on_task_complete = self._on_task_complete
        self.thread_pool.on_task_error = self._on_task_error

    def shutdown(self, wait: bool = True):
        """Drives down the thread pool. Args: Wait: Whether all tasks should be served"""
        self.thread_pool.shutdown(wait)

    def create_batch(self, name: str = None) -> str:
        """Creates a new batch and returns its id. ARGS: Name: Optional name for the Batch Return: The Batch ID"""
        with self._lock:
            self.batch_counter += 1
            batch_id = f"batch_{self.batch_counter}"

            self.batches[batch_id] = {
                'name': name or batch_id,
                'status': 'created',
                'tasks': {},
                'creation_time': time.time(),
                'start_time': None,
                'end_time': None,
                'total_tasks': 0,
                'completed_tasks': 0,
                'failed_tasks': 0
            }

            return batch_id

    def start_batch(self, batch_id: str) -> bool:
        """Starts the execution of a batch. ARGS: Batch_id: The Batch Id Return: True When the Batch Started Successfully, False OtherWise"""
        with self._lock:
            if batch_id not in self.batches:
                logger.error(f"Batch {batch_id} existiert nicht")
                return False

            batch = self.batches[batch_id]
            if batch['status'] != 'created':
                logger.error(f"Batch {batch_id} hat bereits den Status {batch['status']}")
                return False

            batch['status'] = 'running'
            batch['start_time'] = time.time()

            # Callback aufrufen
            if self.on_batch_start:
                try:
                    self.on_batch_start(batch_id, batch)
                except Exception as e:
                    logger.error(f"Fehler im on_batch_start-Callback: {e}")

            return True

    def add_task(self, batch_id: str, func: Callable, *args, **kwargs) -> Optional[str]:
        """Add a Task to a Batch. Args: Batch_id: The Batch Id Func: The Function to Be Carried Out *Args: Position Argents for the Function ** Kwargs: Key Virtues for the Function Return: The Task Id Or None IF the Batch Does not Exist"""
        with self._lock:
            if batch_id not in self.batches:
                logger.error(f"Batch {batch_id} existiert nicht")
                return None

            batch = self.batches[batch_id]
            if batch['status'] not in ['created', 'running']:
                logger.error(f"Batch {batch_id} hat den Status {batch['status']}")
                return None

            # Create task ID for tracking
            task_kwargs = kwargs.copy()
            task_id = task_kwargs.pop('task_id', None) or f"{batch_id}_task_{batch['total_tasks'] + 1}"

            # Add task to the thread pool
            task_id = self.thread_pool.submit(
                func, *args, **task_kwargs, task_id=task_id, batch_id=batch_id
            )

            # Task in Batch registrieren
            batch['tasks'][task_id] = {
                'status': 'submitted',
                'creation_time': time.time()
            }
            batch['total_tasks'] += 1

            return task_id

    def add_tasks_bulk(self, batch_id: str, tasks: List[Tuple[Callable, tuple, dict]]) -> List[Optional[str]]:
        """Add Several Task to a Batch at Once. Args: Batch_id: The Batch Id Tasks: List of (Func, Args, Kwargs) Tuber Return: List of Task Ids Or None Values"""
        task_ids = []

        for func, args, kwargs in tasks:
            task_id = self.add_task(batch_id, func, *args, **kwargs)
            task_ids.append(task_id)

        return task_ids

    def _on_task_complete(self, task: Task):
        """Is called when a task is complete. Args: Task: The Completed Task"""
        batch_id = task.kwargs.get('batch_id')
        if not batch_id:
            return

        with self._lock:
            if batch_id not in self.batches:
                return

            batch = self.batches[batch_id]
            if task.task_id in batch['tasks']:
                batch['tasks'][task.task_id]['status'] = 'completed'
                batch['tasks'][task.task_id]['end_time'] = time.time()
                batch['completed_tasks'] += 1

                # Check whether the batch is complete
                if batch['completed_tasks'] + batch['failed_tasks'] >= batch['total_tasks']:
                    self._finish_batch(batch_id)
                else:
                    # Progress-Callback aufrufen
                    if self.on_batch_progress:
                        try:
                            progress = batch['completed_tasks'] / batch['total_tasks']
                            self.on_batch_progress(batch_id, batch, progress)
                        except Exception as e:
                            logger.error(f"Fehler im on_batch_progress-Callback: {e}")

    def _on_task_error(self, task: Task, error: Exception):
        """Is called when a task fails. Args: Task: The Failed Task Error: The Error Occurred"""
        batch_id = task.kwargs.get('batch_id')
        if not batch_id:
            return

        with self._lock:
            if batch_id not in self.batches:
                return

            batch = self.batches[batch_id]
            if task.task_id in batch['tasks']:
                batch['tasks'][task.task_id]['status'] = 'failed'
                batch['tasks'][task.task_id]['end_time'] = time.time()
                batch['tasks'][task.task_id]['error'] = str(error)
                batch['failed_tasks'] += 1

                # Check whether the batch is complete
                if batch['completed_tasks'] + batch['failed_tasks'] >= batch['total_tasks']:
                    self._finish_batch(batch_id)
                else:
                    # Progress-Callback aufrufen
                    if self.on_batch_progress:
                        try:
                            progress = batch['completed_tasks'] / batch['total_tasks']
                            self.on_batch_progress(batch_id, batch, progress)
                        except Exception as e:
                            logger.error(f"Fehler im on_batch_progress-Callback: {e}")

    def _finish_batch(self, batch_id: str):
        """Complete a Batch. Args: Batch_id: The Batch ID"""
        with self._lock:
            if batch_id not in self.batches:
                return

            batch = self.batches[batch_id]
            batch['status'] = 'completed'
            batch['end_time'] = time.time()

            # Callback aufrufen
            if self.on_batch_complete:
                try:
                    self.on_batch_complete(batch_id, batch)
                except Exception as e:
                    logger.error(f"Fehler im on_batch_complete-Callback: {e}")

    def get_batch_status(self, batch_id: str) -> Optional[Dict]:
        """Gives Back the Status of a Batch. Args: Batch_id: The Batch Id Return: A dictionary with status information or none if the batch does not exist"""
        with self._lock:
            if batch_id not in self.batches:
                return None

            batch = self.batches[batch_id].copy()

            # Calculate additional information
            if batch['status'] == 'running' and batch['total_tasks'] > 0:
                batch['progress'] = batch['completed_tasks'] / batch['total_tasks']

                if batch['start_time']:
                    elapsed = time.time() - batch['start_time']
                    if batch['completed_tasks'] > 0 and elapsed > 0:
                        # Estimate the remaining time
                        items_per_second = batch['completed_tasks'] / elapsed
                        remaining_items = batch['total_tasks'] - batch['completed_tasks']
                        estimated_seconds = remaining_items / items_per_second if items_per_second > 0 else 0

                        batch['elapsed_seconds'] = elapsed
                        batch['estimated_seconds_remaining'] = estimated_seconds

            return batch

    def get_all_batches(self) -> Dict[str, Dict]:
        """Gives Back the Status of All Batches. Return: a dictionary with batch ids as a key and status dictionaries as value"""
        with self._lock:
            return {batch_id: self.get_batch_status(batch_id) for batch_id in self.batches}

    def wait_for_batch(self, batch_id: str, timeout: Optional[float] = None) -> bool:
        """Wait until a batch is complained. Args: Batch_id: The Batch ID Timeout: Optional Timeout in Seconds Return: True When The Batch Has Been Completed, False at Timeout"""
        start_time = time.time()

        while True:
            status = self.get_batch_status(batch_id)

            if not status:
                logger.error(f"Batch {batch_id} existiert nicht")
                return False

            if status['status'] == 'completed':
                return True

            # Check on timeout
            if timeout and time.time() - start_time > timeout:
                return False

            # Short break to protect CPU
            time.sleep(0.1)

# Main function for test purposes
def main():
    """Test function for the adaptive thread pool and batchprocessor."""
    # Logging konfigurieren
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Beispielaufgabe
    def example_task(task_id, sleep_time):
        logger.info(f"Task {task_id} gestartet (Schlafzeit: {sleep_time}s)")
        time.sleep(sleep_time)
        logger.info(f"Task {task_id} abgeschlossen")
        return f"Ergebnis von Task {task_id}"

    # Test for adaptive thread pool
    def test_thread_pool():
        logger.info("Teste AdaptiveThreadPool...")

        pool = AdaptiveThreadPool(min_workers=2, max_workers=8)
        pool.start()

        # Add tasks
        for i in range(20):
            sleep_time = 0.5 + (i % 5) * 0.3  # Vary between 0.5 and 1.7 seconds
            pool.submit(example_task, f"pool_{i}", sleep_time)

        # Warte auf Abschluss
        pool.wait_completion()
        logger.info(f"ThreadPool-Statistiken: {pool.stats}")

        # Pool herunterfahren
        pool.shutdown()
        logger.info("AdaptiveThreadPool-Test abgeschlossen")

    # Test for batchprocessor
    def test_batch_processor():
        logger.info("Teste BatchProcessor...")

        processor = BatchProcessor(min_workers=2, max_workers=8)
        processor.start()

        # Callback for batch progress
        def on_progress(batch_id, batch, progress):
            logger.info(f"Batch {batch_id}: {progress*100:.1f}% abgeschlossen")

        processor.on_batch_progress = on_progress

        # Erstelle einen Batch
        batch_id = processor.create_batch("Testbatch")
        processor.start_batch(batch_id)

        # Add tasks
        for i in range(10):
            sleep_time = 0.2 + (i % 3) * 0.3  # Varized between 0.2 and 0.8 seconds
            processor.add_task(batch_id, example_task, f"batch_{i}", sleep_time)

        # Warte auf Abschluss des Batches
        processor.wait_for_batch(batch_id)
        logger.info(f"Batch-Status: {processor.get_batch_status(batch_id)}")

        # Processor herunterfahren
        processor.shutdown()
        logger.info("BatchProcessor-Test abgeschlossen")

    # Perform tests
    test_thread_pool()
    print("\n" + "-" * 60 + "\n")
    test_batch_processor()

if __name__ == "__main__":
    main()
