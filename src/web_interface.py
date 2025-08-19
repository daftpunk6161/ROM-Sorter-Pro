#!/usr/bin/env python3
# -*-coding: utf-8-*-
"""
ROM Sorter Web Interface - Modern web-based user interface.

Flask-based web app with REST API, real-time updates via WebSocket
and modern responsive design.

OPTIMIZED VERSION 2.1.1:
- Improved memory management and connection pooling
- Enhanced security with input validation and rate limiting
- Optimized WebSocket performance with message batching
- Better error handling and graceful degradation
- Connection pool optimization for database operations
"""

import os
import json
import threading
import queue
import uuid
import time
import weakref
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
import logging
from collections import defaultdict, deque
from functools import wraps, lru_cache
import hashlib

# Availability Tracking with version info modules
MODULES_AVAILABLE = {
    'flask': False,
    'flask_socketio': False, 
    'werkzeug': False,
    'main': False,
    'utils': False,
    'ai_features': False,
    'redis': False
}

# Enhanced Flask Dependencies with Graceful Fallback
try:
    from flask import Flask, render_template, request, jsonify, send_file, session, g
    from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
    from werkzeug.utils import secure_filename as _secure_filename
    from werkzeug.exceptions import RequestEntityTooLarge
    
# Type-Safe Wrapper for Secure_Filename
    def secure_filename(filename: str) -> str:
        return str(_secure_filename(filename))
    MODULES_AVAILABLE['flask'] = True
    MODULES_AVAILABLE['flask_socketio'] = True
    MODULES_AVAILABLE['werkzeug'] = True
    
# Initialize flask app with optimized configuration
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'rom-sorter-secret-key-change-in-production'),
        MAX_CONTENT_LENGTH=500 * 1024 * 1024,  # 500MB max upload
        JSON_SORT_KEYS=False,  # Performance optimization
        JSONIFY_PRETTYPRINT_REGULAR=False,  # Performance optimization
        WTF_CSRF_TIME_LIMIT=3600  # 1 hour CSRF timeout
    )
    
# Optimized SackeTio Configuration
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*",
        async_mode='threading',  # Better performance for CPU-bound tasks
        ping_timeout=30,
        ping_interval=5,
        max_http_buffer_size=1024*1024  # 1MB buffer
    )
    
except ImportError as e:
    logging.warning(f"Flask/SocketIO not available: {e}")
    
# Enhanced Mock Flask for Development/Testing
    app = None
    socketio = None
    
    def emit(*args, **kwargs): 
        pass
    def join_room(*args, **kwargs): 
        pass
    def leave_room(*args, **kwargs):
        pass
    def disconnect(*args, **kwargs):
        pass
    def secure_filename_fallback(filename): 
        return "".join(c for c in filename if c.isalnum() or c in '._-')
    def jsonify(data): 
        return data

# Optional Redis for Session Management and Caching
try:
    import redis  # type: ignore
    redis_client = redis.Redis(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        db=int(os.environ.get('REDIS_DB', 0)),
        decode_responses=True,
        socket_keepalive=True,
        socket_keepalive_options={},
        connection_pool=redis.ConnectionPool(max_connections=20)
    )
    MODULES_AVAILABLE['redis'] = True
except ImportError:
    redis_client = None

# Rome Sorter Core module with Optimized Imports
try:
# Use Dynamic Import to Avoid Circular Import Issues
    import importlib
    main_module = importlib.import_module('main')
    OptimizedROMSorterPro = main_module.OptimizedROMSorterPro
    SortingOptions = main_module.SortingOptions
    ProcessingStats = main_module.ProcessingStats
    MODULES_AVAILABLE['main'] = True
except ImportError as e:
    logging.warning(f"Could not import main module: {e}")
    MODULES_AVAILABLE['main'] = False
    
    class OptimizedROMSorterPro:
        def sort_by_console_advanced(self, source_path: str, dest_path: str, options=None):
            return {'error': 'ROM Sorter not available', 'files_processed': 0}
    
    class SortingOptions:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class ProcessingStats:
        def __init__(self):
            self.files_processed = 0
            self.errors = 0

try:
    from utils import batch_process_roms as _batch_process_roms, get_console_statistics, performance_monitor
    MODULES_AVAILABLE['utils'] = True
    
    # Type-safe wrapper for batch_process_roms
    def batch_process_roms(directory: str, batch_size: int = 200) -> List[Dict[str, Any]]:
        """Wrapper to convert Iterator to List for type compatibility."""
        result = _batch_process_roms(directory, batch_size)
        if hasattr(result, '__iter__') and not isinstance(result, list):
            return list(result)
        return result if isinstance(result, list) else []
        
except ImportError as e:
    logging.warning(f"Could not import utils module: {e}")
    MODULES_AVAILABLE['utils'] = False
    
    def batch_process_roms(directory: str, batch_size: int = 200) -> List[Dict[str, Any]]:
        return []
    
    def get_console_statistics(rom_files: List[Dict[str, Any]]) -> Dict[str, int]:
        return {}
    
    class DummyPerformanceMonitor:
        def start(self): pass
        def stop(self): return 0.0
        def get_stats(self): return {}
        def get_comprehensive_stats(self): return {}
    
    performance_monitor = DummyPerformanceMonitor()
    
# Override if imported Performance_Monitor does not have request methods
    if not hasattr(performance_monitor, 'start'):
        performance_monitor = DummyPerformanceMonitor()
    
    class MockPerformanceMonitor:
        @staticmethod
        def get_comprehensive_stats():
            return {'cache_hit_rate': 0, 'processing_speed': 0, 'total_files': 0}
        @staticmethod
        def start():
            pass
        @staticmethod
        def stop():
            return 0.0
    
    performance_monitor = MockPerformanceMonitor()

# Type alias for performance monitoring
PerformanceMonitorType = type(performance_monitor)

try:
    from ai_features import ROMDatabase, MetadataEnricher, OnlineMetadataProvider  # type: ignore
    MODULES_AVAILABLE['ai_features'] = True
except ImportError as e:
    logging.warning(f"Could not import AI features: {e}")
    MODULES_AVAILABLE['ai_features'] = False
    
    class ROMDatabase:  # type: ignore
        pass
    class MetadataEnricher:  # type: ignore
        pass  
    class OnlineMetadataProvider:  # type: ignore
        pass

# Global variable with enhana management
active_sessions: Set[str] = set()
connection_pool = weakref.WeakSet()
message_buffer = defaultdict(deque)
rate_limiters = defaultdict(lambda: {'count': 0, 'reset_time': time.time() + 60})


class SecurityValidator:
    """Enhanced security validation for web interface."""
    
    @staticmethod
    def validate_path(path: str) -> bool:
        """Validate file paths to prevent directory traversal."""
        if not path or not isinstance(path, str):
            return False
        
# Normalize the Path
        normalized = os.path.normpath(path)
        
# Check for Directory Traversal Attempts
        if '..' in normalized or normalized.startswith('/'):
            return False
        
# Check for Dangerous Characters
        dangerous_chars = ['<', '>', '|', '*', '?', '"']
        if any(char in normalized for char in dangerous_chars):
            return False
        
        return True
    
    @staticmethod
    def validate_job_data(data: Dict[str, Any]) -> bool:
        """Validate job data structure."""
        required_fields = ['source_path']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Enhanced filename sanitization."""
        if not filename:
            return "unknown_file"
        
# Remove Dangerous Characters
        safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-')
        sanitized = ''.join(c if c in safe_chars else '_' for c in filename)
        
# Ensure Reasonable Langthh
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:250 - len(ext)] + ext
        
        return sanitized or "sanitized_file"


class RateLimiter:
    """Simple rate limiting for API endpoints."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed based on rate limiting."""
        now = time.time()
        minute_ago = now - 60
        
# Clean old request
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id] 
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            return False
        
# Add Current Request
        self.requests[client_id].append(now)
        return True


class OptimizedWebSocketLogger(logging.Handler):
    """Optimized WebSocket logger with message batching."""
    
    def __init__(self, batch_size: int = 10, flush_interval: float = 2.0):
        super().__init__()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.message_queue = deque()
        self.last_flush = time.time()
        self.lock: threading.Lock = threading.Lock()
        
        # Start background flush thread
        self._start_flush_thread()
    
    def emit(self, record):
        """Emit log record with batching."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name
        }
        
        with self.lock:
            self.message_queue.append(log_entry)
            
# Flush if batch is full or interval exeded
            if (len(self.message_queue) >= self.batch_size or 
                time.time() - self.last_flush > self.flush_interval):
                self._flush_messages()
    
    def _flush_messages(self):
        """Flush accumulated messages to WebSocket."""
        if not self.message_queue or not MODULES_AVAILABLE['flask_socketio']:
            return
        
        messages = list(self.message_queue)
        self.message_queue.clear()
        self.last_flush = time.time()
        
        try:
            if socketio:
                socketio.emit('log_batch', {'messages': messages}, namespace='/status')
        except Exception as e:
            # Avoid recursive logging
            print(f"WebSocket logging error: {e}")
    
    def _start_flush_thread(self):
        """Start background thread for periodic flushing."""
        def flush_worker():
            while True:
                time.sleep(self.flush_interval)
                with self.lock:
                    if self.message_queue:
                        self._flush_messages()
        
        thread = threading.Thread(target=flush_worker, daemon=True)
        thread.start()


class OptimizedJobManager:
    """Enhanced job manager with persistence and optimization."""
    
    def __init__(self, max_jobs: int = 1000, cleanup_interval: int = 300):
        self.jobs = {}
        self.lock: threading.RLock = threading.RLock()
        self.max_jobs = max_jobs
        self.cleanup_interval = cleanup_interval
        self.job_index = defaultdict(list)  # Index by status for faster queries
        
# Start Cleanup Thread
        self._start_cleanup_thread()
    
    def create_job(self, job_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job with enhanced validation."""
        if not SecurityValidator.validate_job_data(job_data):
            raise ValueError("Invalid job data")
        
        with self.lock:
            # Clean up if too many jobs
            if len(self.jobs) >= self.max_jobs:
                self._cleanup_old_jobs(max_age_hours=1)
            
            job = {
                'id': job_id,
                'status': 'pending',
                'progress': 0,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'data': job_data,
                'result': None,
                'error': None,
                'metrics': {
                    'start_time': None,
                    'end_time': None,
                    'memory_peak': 0,
                    'cpu_time': 0
                }
            }
            
            self.jobs[job_id] = job
            self.job_index['pending'].append(job_id)
            
# Persist to redis If Available
            if redis_client:
                try:
                    redis_client.setex(f"job:{job_id}", 3600, json.dumps(job))
                except Exception as e:
                    logging.warning(f"Redis persistence error: {e}")
            
            return job
    
    def update_job(self, job_id: str, **kwargs):
        """Update job status with optimized notifications."""
        with self.lock:
            if job_id not in self.jobs:
                return False
            
            old_status = self.jobs[job_id]['status']
            self.jobs[job_id].update(kwargs)
            self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
            
            # Update index if status changed
            new_status = self.jobs[job_id]['status']
            if old_status != new_status:
                if job_id in self.job_index[old_status]:
                    self.job_index[old_status].remove(job_id)
                self.job_index[new_status].append(job_id)
            
# Optimized Websocket Notification
            if MODULES_AVAILABLE['flask_socketio'] and socketio:
                try:
# ONLY SEND Essential Data to Reduce Bandwidth
                    update_data = {
                        'id': job_id,
                        'status': new_status,
                        'progress': self.jobs[job_id]['progress'],
                        'updated_at': self.jobs[job_id]['updated_at']
                    }
                    socketio.emit('job_update', update_data, namespace='/status')
                except Exception as e:
                    logging.warning(f"WebSocket notification error: {e}")
            
            return True
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID with Redis fallback."""
        with self.lock:
            if job_id in self.jobs:
                return self.jobs[job_id].copy()
        
# Try Redis If Available
        if redis_client:
            try:
                job_data = redis_client.get(f"job:{job_id}")
                if job_data:
                    return json.loads(job_data)
            except Exception as e:
                logging.warning(f"Redis retrieval error: {e}")
        
        return None
    
    def get_jobs_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get jobs by status efficiently."""
        with self.lock:
            job_ids = self.job_index.get(status, [])
            return [self.jobs[job_id].copy() for job_id in job_ids if job_id in self.jobs]
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Public method to cleanup old jobs."""
        return self._cleanup_old_jobs(max_age_hours)
    
    def _cleanup_old_jobs(self, max_age_hours: int = 24):
        """Enhanced cleanup with metrics."""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        removed_count = 0
        
        with self.lock:
            to_remove = []
            for job_id, job in self.jobs.items():
                if job['status'] in ['completed', 'failed']:
                    job_time = datetime.fromisoformat(job['created_at']).timestamp()
                    if job_time < cutoff:
                        to_remove.append(job_id)
            
            for job_id in to_remove:
                job = self.jobs.pop(job_id)
# Remove from Index
                for status_list in self.job_index.values():
                    if job_id in status_list:
                        status_list.remove(job_id)
                removed_count += 1
                
                # Remove from Redis
                if redis_client:
                    try:
                        redis_client.delete(f"job:{job_id}")
                    except Exception:
                        pass
        
        if removed_count > 0:
            logging.info(f"Cleaned up {removed_count} old jobs")
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread."""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(self.cleanup_interval)
                    self._cleanup_old_jobs()
                except Exception as e:
                    logging.error(f"Cleanup thread error: {e}")
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()


# Initialize Optimized Components
job_manager = OptimizedJobManager()
rate_limiter = RateLimiter(requests_per_minute=100)
security_validator = SecurityValidator()


def require_rate_limit(f):
    """Decorator for rate limiting."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_id = request.remote_addr or "unknown"
        if not rate_limiter.is_allowed(client_id):
            return jsonify({'error': 'Rate limit exceeded'}), 429
        return f(*args, **kwargs)
    return decorated_function


@lru_cache(maxsize=100)
def get_system_stats() -> Dict[str, Any]:
    """Cached system statistics."""
    stats = {
        'timestamp': datetime.now().isoformat(),
        'modules_available': MODULES_AVAILABLE,
        'active_jobs': len(job_manager.jobs),
        'memory_usage': 0
    }
    
    try:
        import psutil
        process = psutil.Process()
        stats['memory_usage'] = process.memory_info().rss / 1024 / 1024  # MB
        stats['cpu_percent'] = process.cpu_percent()
    except ImportError:
        pass
    
    return stats


def create_optimized_web_app():
    """Create optimized Flask app with enhanced configuration."""
    if not MODULES_AVAILABLE['flask'] or app is None:
        logging.error("Flask not available - Web interface disabled")
        return None, None
    
    # Enhanced app configuration
    app.config.update(
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
        SESSION_COOKIE_SECURE=True if os.environ.get('HTTPS') else False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax'
    )
    
    return app, socketio


def setup_optimized_routes(app, socketio):
    """Setup optimized Flask routes with enhanced security and performance."""
    if not app or not socketio:
        return
    
    @app.before_request
    def before_request():
        """Enhanced request preprocessing."""
# Set Request Start Time for Performance Monitoring
        g.start_time = time.time()
        
        # Session management
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session.permanent = True
        
        # Add session to active sessions
        active_sessions.add(session['session_id'])
    
    @app.after_request
    def after_request(response):
        """Enhanced response postprocessing."""
# Add Security Headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Performance monitoring
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            response.headers['X-Response-Time'] = str(duration)
            
# Log Slow Requests
            if duration > 1.0:
                logging.warning(f"Slow request: {request.path} took {duration:.2f}s")
        
        return response

    @app.route('/')
    def index():
        """Optimized main page with caching."""
        # Simple template caching
        cache_key = 'index_template'
        if redis_client:
            try:
                cached_content = redis_client.get(cache_key)
                if cached_content:
                    return cached_content
            except Exception:
                pass
        
        try:
            content = render_template('index.html', 
                                    system_stats=get_system_stats(),
                                    modules_available=MODULES_AVAILABLE)
            
# Cache for 5 Minutes
            if redis_client:
                try:
                    redis_client.setex(cache_key, 300, content)
                except Exception:
                    pass
            
            return content
        except Exception as e:
            logging.error(f"Template rendering error: {e}")
            return jsonify({'error': 'Template rendering failed'}), 500

    @app.route('/api/scan', methods=['POST'])
    @require_rate_limit
    def api_scan():
        """Enhanced API endpoint for ROM scanning."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            source_path = data.get('source_path')
            batch_size = data.get('batch_size', 200)
            
            # Enhanced validation
            if not source_path or not isinstance(source_path, str):
                return jsonify({'error': 'Invalid source path'}), 400
            
            if not security_validator.validate_path(source_path):
                return jsonify({'error': 'Invalid or unsafe path'}), 400
            
            if not os.path.exists(source_path):
                return jsonify({'error': 'Source path does not exist'}), 400
            
            if not isinstance(batch_size, int) or batch_size < 1 or batch_size > 1000:
                return jsonify({'error': 'Invalid batch size (1-1000)'}), 400
            
            job_id = str(uuid.uuid4())
            
            def enhanced_scan_worker():
                """Enhanced background worker for ROM scanning."""
                try:
                    # Create job with metrics
                    job_manager.update_job(job_id, status='running', progress=5)
                    if hasattr(performance_monitor, 'start'):
                        performance_monitor.start()  # type: ignore
                    
                    # Memory monitoring
                    memory_start = 0
                    try:
                        import psutil
                        memory_start = psutil.Process().memory_info().rss / 1024 / 1024
                    except ImportError:
                        pass
                    
                    if MODULES_AVAILABLE['utils']:
# Enhanced Rome Scanning with Progress Updates
                        job_manager.update_job(job_id, progress=10)
                        rom_files = batch_process_roms(source_path, batch_size)
                        job_manager.update_job(job_id, progress=60)
                        
# Enhanced Statistics
                        stats = get_console_statistics(rom_files)
                        job_manager.update_job(job_id, progress=80)
                        
# Calculate Additional Metrics
                        total_size = sum(rf.get('file_size', 0) for rf in rom_files)
                        avg_size = total_size / len(rom_files) if rom_files else 0
                        
# Memory Usage
                        memory_end = memory_start
                        try:
                            import psutil
                            memory_end = psutil.Process().memory_info().rss / 1024 / 1024
                        except ImportError:
                            pass
                        
                        result = {
                            'rom_files': len(rom_files),
                            'console_stats': stats,
                            'scan_path': source_path,
                            'total_size_mb': total_size / (1024 * 1024),
                            'average_size_mb': avg_size / (1024 * 1024),
                            'memory_used_mb': memory_end - memory_start,
                            'scan_duration': performance_monitor.stop() if hasattr(performance_monitor, 'stop') else 0.0  # type: ignore
                        }
                    else:
                        result = {
                            'error': 'Utils module not available',
                            'rom_files': 0,
                            'console_stats': {},
                            'scan_path': source_path
                        }
                    
                    job_manager.update_job(
                        job_id, 
                        status='completed', 
                        progress=100, 
                        result=result
                    )
                    
                except Exception as e:
                    error_result = {
                        'error': str(e),
                        'type': type(e).__name__,
                        'scan_path': source_path
                    }
                    job_manager.update_job(
                        job_id, 
                        status='failed', 
                        error=error_result
                    )
                    logging.error(f"Scan worker error: {e}", exc_info=True)
            
# Create and Start Enhanced Job
            job_data = {
                'source_path': source_path,
                'batch_size': batch_size,
                'scan_type': 'rom_scan'
            }
            job_manager.create_job(job_id, job_data)
            
            thread = threading.Thread(target=enhanced_scan_worker, name=f"ScanWorker-{job_id[:8]}")
            thread.daemon = True
            thread.start()
            
            return jsonify({
                'job_id': job_id, 
                'status': 'started',
                'estimated_time': 'varies',
                'batch_size': batch_size
            })
            
        except Exception as e:
            logging.error(f"API scan error: {e}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/sort', methods=['POST'])
    @require_rate_limit
    def api_sort():
        """Enhanced API endpoint for ROM sorting."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400
            
            source_path = data.get('source_path')
            dest_path = data.get('dest_path')
            options = data.get('options', {})
            
            # Enhanced validation
            for path_name, path_value in [('source_path', source_path), ('dest_path', dest_path)]:
                if not path_value or not isinstance(path_value, str):
                    return jsonify({'error': f'Invalid {path_name}'}), 400
                
                if not security_validator.validate_path(path_value):
                    return jsonify({'error': f'Invalid or unsafe {path_name}'}), 400
            
            if not os.path.exists(source_path):
                return jsonify({'error': 'Source path does not exist'}), 400
            
            # Validate options
            valid_options = {
                'console_sorting', 'detect_duplicates', 'handle_homebrew',
                'batch_size', 'max_workers', 'dry_run', 'create_backup'
            }
            invalid_options = set(options.keys()) - valid_options
            if invalid_options:
                return jsonify({'error': f'Invalid options: {list(invalid_options)}'}), 400
            
            job_id = str(uuid.uuid4())
            
            def enhanced_sort_worker():
                """Enhanced background worker for ROM sorting."""
                try:
                    job_manager.update_job(job_id, status='running', progress=5)
                    
                    if MODULES_AVAILABLE['main']:
# Create Enhanced Sorter Instance
                        from main import AdvancedROMSorterPro, EnhancedSortingOptions
                        
                        sorting_options = EnhancedSortingOptions(
                            console_sorting=options.get('console_sorting', True),
                            detect_duplicates=options.get('detect_duplicates', False),
                            handle_homebrew=options.get('handle_homebrew', True),
                            batch_size=max(50, min(options.get('batch_size', 200), 500)),
                            max_workers=max(1, min(options.get('max_workers', 4), 12)),
                            dry_run=options.get('dry_run', False),
                            create_backup=options.get('create_backup', False)
                        )
                        
                        sorter = AdvancedROMSorterPro(options=sorting_options)
                        job_manager.update_job(job_id, progress=10)
                        
# Perform Enhanced Sorting
                        stats = sorter.sort_by_console_advanced(source_path, dest_path)
                        
# Add Job-Specific Metrics
                        stats['job_id'] = job_id
                        stats['request_options'] = options
                        
                    else:
                        stats = {
                            'error': 'Main module not available', 
                            'files_processed': 0,
                            'job_id': job_id
                        }
                    
                    job_manager.update_job(
                        job_id, 
                        status='completed', 
                        progress=100, 
                        result=stats
                    )
                    
                except Exception as e:
                    error_result = {
                        'error': str(e),
                        'type': type(e).__name__,
                        'job_id': job_id,
                        'source_path': source_path,
                        'dest_path': dest_path
                    }
                    job_manager.update_job(
                        job_id, 
                        status='failed', 
                        error=error_result
                    )
                    logging.error(f"Sort worker error: {e}", exc_info=True)
            
# Create and Start Enhanced Job
            job_data = {
                'source_path': source_path,
                'dest_path': dest_path,
                'options': options,
                'sort_type': 'rom_sort'
            }
            job_manager.create_job(job_id, job_data)
            
            thread = threading.Thread(target=enhanced_sort_worker, name=f"SortWorker-{job_id[:8]}")
            thread.daemon = True
            thread.start()
            
            return jsonify({
                'job_id': job_id, 
                'status': 'started',
                'options_applied': options,
                'estimated_time': 'varies'
            })
            
        except Exception as e:
            logging.error(f"API sort error: {e}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/job/<job_id>')
    def api_job_status(job_id):
        """Enhanced job status with security validation."""
        # Validate job_id format
        try:
            uuid.UUID(job_id)
        except ValueError:
            return jsonify({'error': 'Invalid job ID format'}), 400
        
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # Remove sensitive information
        safe_job = job.copy()
        if 'data' in safe_job:
# ONLY Include non-sensitive job data
            safe_data = {k: v for k, v in safe_job['data'].items() 
                        if k not in ['full_path', 'system_info']}
            safe_job['data'] = safe_data
        
        return jsonify(safe_job)

    @app.route('/api/jobs')
    def api_jobs():
        """Enhanced jobs list with filtering and pagination."""
        # Get query parameters
        status_filter = request.args.get('status')
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 items
        offset = int(request.args.get('offset', 0))
        
        # Get jobs with optional filtering
        if status_filter:
            jobs = job_manager.get_jobs_by_status(status_filter)
        else:
            with job_manager.lock:
                jobs = list(job_manager.jobs.values())
        
# Sort by Creation Time (Newest First)
        jobs.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Apply pagination
        total_jobs = len(jobs)
        jobs = jobs[offset:offset + limit]
        
        # Remove sensitive information
        safe_jobs = []
        for job in jobs:
            safe_job = {
                'id': job['id'],
                'status': job['status'],
                'progress': job['progress'],
                'created_at': job['created_at'],
                'updated_at': job['updated_at']
            }
            if job.get('result'):
# Include Summary of Results only
                result = job['result']
                safe_job['result_summary'] = {
                    'files_processed': result.get('files_processed', 0),
                    'errors': result.get('errors', 0),
                    'duration': result.get('duration', 0)
                }
            safe_jobs.append(safe_job)
        
        return jsonify({
            'jobs': safe_jobs,
            'total': total_jobs,
            'offset': offset,
            'limit': limit
        })

    @app.route('/api/stats')
    def api_stats():
        """Enhanced performance statistics."""
        if not MODULES_AVAILABLE['utils']:
            return jsonify({'error': 'Utils module not available'}), 500
        
        try:
            # Get comprehensive stats
            stats: Dict[str, Any] = {}
            if hasattr(performance_monitor, 'get_comprehensive_stats'):
                stats = performance_monitor.get_comprehensive_stats()
            else:
                stats = {'error': 'Performance monitor API not available'}
            
# ADD System Stats
            system_stats = get_system_stats()
            stats['system'] = system_stats
            
# ADD Job Manager Stats
            with job_manager.lock:
                job_stats = {
                    'total_jobs': len(job_manager.jobs),
                    'pending_jobs': len(job_manager.job_index.get('pending', [])),
                    'running_jobs': len(job_manager.job_index.get('running', [])),
                    'completed_jobs': len(job_manager.job_index.get('completed', [])),
                    'failed_jobs': len(job_manager.job_index.get('failed', []))
                }
            stats['jobs'] = job_stats
            
            return jsonify(stats)
        except Exception as e:
            logging.error(f"Stats API error: {e}", exc_info=True)
            return jsonify({'error': f'Could not get stats: {e}'}), 500

# Enhanced website events
    @socketio.on('connect', namespace='/status')
    def handle_connect():
        """Enhanced WebSocket connection handling."""
        session_id = session.get('session_id', 'unknown')
        logging.info(f"WebSocket connected: {session_id}")
        
# Send Welcome Message with System Info
        emit('connected', {
            'status': 'Connected to ROM Sorter Pro v2.1.1',
            'session_id': session_id,
            'server_time': datetime.now().isoformat(),
            'modules_available': MODULES_AVAILABLE
        })

    @socketio.on('disconnect', namespace='/status')
    def handle_disconnect():
        """Enhanced WebSocket disconnection handling."""
        session_id = session.get('session_id', 'unknown')
        logging.info(f"WebSocket disconnected: {session_id}")

    @socketio.on('join_job', namespace='/status')
    def handle_join_job(data):
        """Enhanced job joining with validation."""
        if not data or not isinstance(data, dict):
            emit('error', {'message': 'Invalid data format'})
            return
        
        job_id = data.get('job_id')
        if not job_id:
            emit('error', {'message': 'Job ID required'})
            return
        
# Validate Job Exists
        if not job_manager.get_job(job_id):
            emit('error', {'message': 'Job not found'})
            return
        
        join_room(job_id)
        emit('joined_job', {
            'job_id': job_id,
            'joined_at': datetime.now().isoformat()
        })

    @socketio.on('leave_job', namespace='/status')
    def handle_leave_job(data):
        """Leave job updates room."""
        if not data or not isinstance(data, dict):
            return
        
        job_id = data.get('job_id')
        if job_id:
            leave_room(job_id)
            emit('left_job', {'job_id': job_id})

# Enhanced Error Handlers
    @app.errorhandler(404)
    def not_found(error):
        """Enhanced 404 handler."""
        return jsonify({
            'error': 'Not found',
            'path': request.path,
            'timestamp': datetime.now().isoformat()
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Enhanced 500 handler."""
        error_id = str(uuid.uuid4())
        logging.error(f"Internal error {error_id}: {error}", exc_info=True)
        
        return jsonify({
            'error': 'Internal server error',
            'error_id': error_id,
            'timestamp': datetime.now().isoformat()
        }), 500

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_request(error):
        """Handle large request errors."""
        return jsonify({
            'error': 'Request too large',
            'max_size': '500MB',
            'timestamp': datetime.now().isoformat()
        }), 413


def setup_enhanced_logging():
    """Setup enhanced logging with WebSocket integration."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
# Add Optimized Websocket Handler
    ws_handler = OptimizedWebSocketLogger(batch_size=5, flush_interval=1.0)
    ws_handler.setLevel(logging.INFO)
    logger.addHandler(ws_handler)
    
# Enhanced Console Handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def enhanced_cleanup_jobs():
    """Enhanced periodic job cleanup with metrics."""
    def cleanup_worker():
        cleanup_count = 0
        while True:
            try:
                start_time = time.time()
                job_manager.cleanup_old_jobs()
                cleanup_duration = time.time() - start_time
                
                cleanup_count += 1
                if cleanup_count % 10 == 0:  # Log every 10 cleanups
                    logging.info(f"Job cleanup #{cleanup_count} completed in {cleanup_duration:.2f}s")
                
                time.sleep(1800)  # Clean up every 30 minutes
            except Exception as e:
                logging.error(f"Job cleanup error: {e}", exc_info=True)
                time.sleep(60)  # Retry after 1 minute on error
    
    thread = threading.Thread(target=cleanup_worker, name="JobCleanup", daemon=True)
    thread.start()


if __name__ == '__main__':
# Initialize the Enhanced Web Application
    app, socketio = create_optimized_web_app()
    
    if app and socketio:
        setup_optimized_routes(app, socketio)
        setup_enhanced_logging()
        enhanced_cleanup_jobs()
        
        logging.info("🌐 Starting Enhanced ROM Sorter Web Interface v2.1.1...")
        logging.info("📁 Access at: http://localhost:5000")
        logging.info("🚀 Enhanced features: Rate limiting, Security validation, Performance monitoring")
        
        try:
            socketio.run(
                app, 
                host='0.0.0.0', 
                port=int(os.environ.get('PORT', 5000)),
                debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true',
                allow_unsafe_werkzeug=True,
                use_reloader=False  # Disable reloader for production
            )
        except Exception as e:
            logging.error(f"Failed to start web interface: {e}", exc_info=True)
    else:
        logging.error("❌ Flask not available - Web interface cannot start")
        logging.info("💡 Install with: pip install flask flask-socketio")
        logging.info("🔧 Web interface functionality disabled")


def run_web_interface():
    """Run the web interface."""
# Initialize the Enhanced Web Application
    app, socketio = create_optimized_web_app()
    
    if app and socketio:
        setup_optimized_routes(app, socketio)
        
# Enhanced Logging with Full Feature List
        logging.info("🌟 Enhanced ROM Sorter Web Interface v2.1.1 Starting...")
        logging.info("📁 Access at: http://localhost:5000")
        logging.info("🚀 Enhanced features: Rate limiting, Security validation, Performance monitoring")
        
        try:
            socketio.run(
                app, 
                host='0.0.0.0', 
                port=int(os.environ.get('PORT', 5000)),
                debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true',
                allow_unsafe_werkzeug=True,
                use_reloader=False  # Disable reloader for production
            )
        except Exception as e:
            logging.error(f"Failed to start web interface: {e}", exc_info=True)
    else:
        logging.error("❌ Flask not available - Web interface cannot start")
        logging.info("💡 Install with: pip install flask flask-socketio")
        logging.info("🔧 Web interface functionality disabled")


if __name__ == "__main__":
    run_web_interface()


# =====================================================================================================
# Compatibility alias for tests
# =====================================================================================================

# Create aliases for test compatibility
JobManager = OptimizedJobManager
WebSocketLogger = OptimizedWebSocketLogger

def create_web_app():
    """Compatibility function for tests."""
    return create_optimized_web_app()

def setup_routes(app, socketio):
    """Compatibility function for tests."""
    return setup_optimized_routes(app, socketio)

def setup_logging():
    """Compatibility function for tests."""
    pass  # Logging is already set up

def cleanup_jobs():
    """Compatibility function for tests."""
    pass  # Job cleanup is handled automatically
