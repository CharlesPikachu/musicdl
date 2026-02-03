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


class GUIProgress:
    """
    A dummy replacement for rich.progress.Progress.
    Used to suppress console output in GUI mode.
    """
    
    def __init__(self, *args, **kwargs):
        self.tasks = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def add_task(self, description, total=None, **kwargs):
        task_id = float(len(self.tasks))
        self.tasks[task_id] = _TaskMock(description=description, total=total)
        return task_id
    
    def update(self, task_id, **kwargs):
        if task_id in self.tasks:
            t = self.tasks[task_id]
            if 'total' in kwargs:
                t.total = kwargs['total']
            if 'completed' in kwargs:
                t.completed = kwargs['completed']
            if 'description' in kwargs:
                t.description = kwargs['description']
    
    def advance(self, task_id, advance=1):
        if task_id in self.tasks:
            self.tasks[task_id].completed += advance
    
    def __getitem__(self, item):
        return self.tasks.get(item, _TaskMock())


class _TaskMock:
    """Mock task object for GUIProgress."""
    
    def __init__(self, description="", total=0, completed=0):
        self.description = description
        self.total = total or 0
        self.completed = completed or 0


class GlobalLogSignal(QObject):
    """Global signal for thread-safe logging."""
    log = pyqtSignal(str, str)


class GUILoggerHandle(LoggerHandle):
    """
    Logger handle that emits signals for GUI display.
    """
    
    # Class-level signal reference (set by MainWindow)
    _log_signal: Optional[GlobalLogSignal] = None
    
    def __init__(self):
        super().__init__()
        self.log_level = logging.WARNING
    
    @classmethod
    def set_log_signal(cls, signal: GlobalLogSignal):
        """Set the global log signal for all instances."""
        cls._log_signal = signal
    
    def _emit(self, level: int, message: str):
        if self._log_signal:
            self._log_signal.log.emit(logging.getLevelName(level), str(message))
    
    def log(self, level: int, message: str):
        if level < self.log_level:
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
