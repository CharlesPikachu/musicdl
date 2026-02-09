# Background Task Workers
"""
Threading and logging utilities for background tasks.
"""

import logging
import traceback
from typing import Any, Callable, Optional

from PyQt6.QtCore import QThread, pyqtSignal, QObject

# Try to import LoggerHandle
try:
    from modules.utils import LoggerHandle
except ImportError:
    try:
        from musicdl.modules.utils import LoggerHandle
    except ImportError:
        # Fallback base class
        class LoggerHandle:
            def __init__(self): pass



class GUIProgressSignal(QObject):
    """Signal for progress updates."""
    # task_id, completed, total, speed, eta, description
    progress = pyqtSignal(float, float, float, str, str, str)


class GUIProgress:
    """
    A replacement for rich.progress.Progress that emits signals for GUI.
    Calculates speed and ETA.
    """
    
    _default_signal: Optional['GUIProgressSignal'] = None

    def __init__(self, *args, signal: Optional[GUIProgressSignal] = None, **kwargs):
        self._tasks = {}
        # Use provided signal or fallback to default
        self.signal = signal if signal is not None else self._default_signal
        self._start_times = {}
        self._last_update_time = {}

    @classmethod
    def set_default_signal(cls, signal: Optional['GUIProgressSignal']):
        """Set the default signal to be used when none is provided."""
        cls._default_signal = signal

    @property
    def tasks(self):
        return self._tasks
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def add_task(self, description, total=None, **kwargs):
        import time
        task_id = float(len(self._tasks))
        self._tasks[task_id] = _TaskMock(description=description, total=total)
        self._start_times[task_id] = time.time()
        self._last_update_time[task_id] = time.time()
        return task_id
    
    def update(self, task_id, **kwargs):
        if task_id not in self._tasks:
            return
            
        t = self._tasks[task_id]
        import time
        now = time.time()
        
        if 'total' in kwargs:
            t.total = kwargs['total']
        if 'completed' in kwargs:
            t.completed = kwargs['completed']
        if 'description' in kwargs:
            t.description = kwargs['description']
        
        # Calculate Speed and ETA
        elapsed = now - self._start_times.get(task_id, now)
        speed_str = "--"
        eta_str = "--"
        
        if elapsed > 0 and t.completed > 0:
            speed = t.completed / elapsed
            # Format speed
            if speed < 1024:
                speed_str = f"{speed:.1f} B/s"
            elif speed < 1024 * 1024:
                speed_str = f"{speed/1024:.1f} KB/s"
            else:
                speed_str = f"{speed/1024/1024:.1f} MB/s"
                
            # Calc ETA
            if t.total > 0 and speed > 0:
                remaining_bytes = t.total - t.completed
                eta_seconds = remaining_bytes / speed
                if eta_seconds < 60:
                    eta_str = f"{int(eta_seconds)}s"
                elif eta_seconds < 3600:
                    eta_str = f"{int(eta_seconds//60)}m {int(eta_seconds%60)}s"
                else:
                    eta_str = f"{int(eta_seconds//3600)}h {int((eta_seconds%3600)//60)}m"

        if self.signal:
            self.signal.progress.emit(
                float(task_id), 
                float(t.completed), 
                float(t.total), 
                speed_str, 
                eta_str, 
                t.description
            )
    
    def advance(self, task_id, advance=1):
        if task_id in self._tasks:
            self._tasks[task_id].completed += advance
            self.update(task_id) # Trigger signal update
    
    def __getitem__(self, item):
        return self._tasks.get(item, _TaskMock())


class _TaskMock:
    """Mock task object for GUIProgress."""
    
    def __init__(self, description="", total=0, completed=0):
        self.description = description
        self.total = total or 0
        self.completed = completed or 0
        self.fields = {} # Support for .fields access if needed


class GlobalLogSignal(QObject):
    """Global signal for thread-safe logging."""
    log = pyqtSignal(str, str)


class GUILoggerHandle(LoggerHandle):
    """
    Logger handle that emits signals for GUI display.
    """
    
    # Class-level signal reference (set by MainWindow)
    _log_signal: Optional[GlobalLogSignal] = None
    # Class-level log level (shared by all instances)
    _log_level: int = logging.WARNING
    
    def __init__(self):
        super().__init__()
    
    @property
    def log_level(self):
        return GUILoggerHandle._log_level
    
    @log_level.setter
    def log_level(self, value):
        GUILoggerHandle._log_level = value
    
    @classmethod
    def set_log_signal(cls, signal: GlobalLogSignal):
        """Set the global log signal for all instances."""
        cls._log_signal = signal
    
    @classmethod
    def set_log_level(cls, level: int):
        """Set the global log level for all instances."""
        cls._log_level = level
    
    def _emit(self, level: int, message: str):
        if self._log_signal:
            self._log_signal.log.emit(logging.getLevelName(level), str(message))
    
    def log(self, level: int, message: str):
        if level < self._log_level:
            return
        self._emit(level, message)
    
    def debug(self, message, disable_print=False):
        self.log(logging.DEBUG, message)
    
    def info(self, message, disable_print=False):
        self.log(logging.INFO, message)
    
    def warning(self, message, disable_print=False):
        self.log(logging.WARNING, message)
    
    def error(self, message, disable_print=False):
        self.log(logging.ERROR, message)


class Worker(QThread):
    """
    Generic worker thread for running background tasks.
    
    Signals:
        finished: Emitted when task completes successfully with result dict
        error: Emitted when task fails with error message
    """
    
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit({'data': result})
        except Exception as e:
            traceback.print_exc()
            self.error.emit(str(e))
