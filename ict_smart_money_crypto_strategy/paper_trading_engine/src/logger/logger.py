"""
Centralized Logging System with Colorful Console Output
Provides consistent logging across all modules with error handling
"""

import logging
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Get project root (3 levels up from this file: src/logger/logger.py -> src/logger -> src -> project_root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Global variable to store current log file path
_current_log_file = None


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
        'BOLD': '\033[1m',        # Bold
    }

    # Emoji/symbols for each level
    SYMBOLS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨',
    }

    def format(self, record):
        """Format log record with colors"""
        # Get color and symbol for this level
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        symbol = self.SYMBOLS.get(record.levelname, '•')
        reset = self.COLORS['RESET']
        bold = self.COLORS['BOLD']

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')

        # Format module name (shortened)
        module = record.name.split('.')[-1][:15].ljust(15)

        # Build colored message
        level_name = f"{color}{bold}{record.levelname:8}{reset}"

        # Format the message
        formatted = f"{symbol} {timestamp} | {level_name} | {module} | {record.getMessage()}"

        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


class FileFormatter(logging.Formatter):
    """Standard formatter for file output (no colors)"""

    def format(self, record):
        """Format log record for file"""
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        module = record.name
        level = record.levelname

        formatted = f"{timestamp} | {level:8} | {module:30} | {record.getMessage()}"

        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def setup_logger(
    name: str,
    log_file: str = None,
    console_level: str = 'INFO',
    file_level: str = 'DEBUG'
) -> logging.Logger:
    """
    Setup logger with colorful console and detailed file output

    Args:
        name: Logger name (usually __name__)
        log_file: Log file path (if None, creates timestamped file)
        console_level: Console log level (INFO, ERROR only by default)
        file_level: File log level (everything)

    Returns:
        Configured logger instance
    """
    global _current_log_file

    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # Capture everything
    logger.propagate = False  # Don't propagate to root logger

    # Console handler - INFO and ERROR only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level))
    console_handler.setFormatter(ColoredFormatter())

    # Add filter to console to exclude DEBUG only (show INFO, WARNING, ERROR, CRITICAL)
    class ExcludeDebugFilter(logging.Filter):
        def filter(self, record):
            return record.levelno >= logging.INFO  # INFO and above (excludes DEBUG)

    console_handler.addFilter(ExcludeDebugFilter())
    logger.addHandler(console_handler)

    # File handler - Everything (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    try:
        # Create timestamped log file name if not provided
        if log_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            logs_dir = PROJECT_ROOT / 'trading_data' / 'logs'
            logs_dir.mkdir(parents=True, exist_ok=True)
            log_file = logs_dir / f'paper_trading_{timestamp}.log'

        _current_log_file = log_file

        file_handler = logging.FileHandler(str(log_file), mode='a', encoding='utf-8')
        file_handler.setLevel(getattr(logging, file_level))
        file_handler.setFormatter(FileFormatter())
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create log file handler: {e}")

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get or create logger for a module

    Args:
        name: Module name (usually __name__)

    Returns:
        Logger instance
    """
    if name is None:
        name = __name__

    return setup_logger(name)


def move_log_to_folder():
    """
    Move current log file to logs/ folder
    Called when the bot stops
    """
    global _current_log_file

    if _current_log_file is None:
        return

    try:
        # Create logs folder if it doesn't exist
        logs_folder = PROJECT_ROOT / 'trading_data' / 'logs'
        logs_folder.mkdir(parents=True, exist_ok=True)

        # Get source and destination paths
        source = Path(_current_log_file)
        if not source.exists():
            return

        destination = logs_folder / source.name

        # Close all file handlers to release the file
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                root_logger.removeHandler(handler)

        # Close all handlers for all loggers
        for logger_name in logging.Logger.manager.loggerDict:
            logger_instance = logging.getLogger(logger_name)
            for handler in logger_instance.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    logger_instance.removeHandler(handler)

        # Move the file
        shutil.move(str(source), str(destination))
        print(f"✅ Log file moved to: {destination}")

    except Exception as e:
        print(f"Warning: Could not move log file: {e}")


# Create a default logger for immediate use
logger = get_logger('paper_trading')


# Exception handling decorator
def log_exceptions(logger_instance=None):
    """
    Decorator to catch and log exceptions

    Usage:
        @log_exceptions()
        def my_function():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_logger = logger_instance or logging.getLogger(func.__module__)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                func_logger.error(
                    f"Exception in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator


# Safe execution context manager
class safe_execution:
    """
    Context manager for safe execution with logging

    Usage:
        with safe_execution("Fetching data", logger):
            # Your code here
            data = fetch_data()
    """

    def __init__(self, operation_name: str, logger_instance=None, raise_on_error=True):
        self.operation_name = operation_name
        self.logger = logger_instance or logger
        self.raise_on_error = raise_on_error

    def __enter__(self):
        self.logger.debug(f"Starting: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.logger.error(
                f"Error in {self.operation_name}: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb)
            )
            return not self.raise_on_error  # Suppress exception if raise_on_error=False
        else:
            self.logger.debug(f"Completed: {self.operation_name}")
        return False


if __name__ == "__main__":
    """Test the logging system"""
    test_logger = get_logger('test_module')

    test_logger.debug("This is a DEBUG message (file only)")
    test_logger.info("This is an INFO message (console + file)")
    test_logger.warning("This is a WARNING message (file only)")
    test_logger.error("This is an ERROR message (console + file)")

    # Test exception logging
    try:
        raise ValueError("Test exception")
    except Exception as e:
        test_logger.error("Caught exception", exc_info=True)

    # Test decorator
    @log_exceptions()
    def test_function():
        raise RuntimeError("Test error in function")

    try:
        test_function()
    except:
        pass

    # Test context manager
    with safe_execution("test operation", test_logger, raise_on_error=False):
        raise Exception("Test context manager error")

    print("\n✅ Logger test complete! Check paper_trading.log for full output")
