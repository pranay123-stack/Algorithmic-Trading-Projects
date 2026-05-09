"""
Unit Tests for Logging System
Tests colorful logging and error handling utilities
"""

import unittest
import sys
import os
import logging
from io import StringIO

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logger.logger import get_logger, safe_execution, log_exceptions


class TestLogger(unittest.TestCase):
    """Test logger functionality"""

    def setUp(self):
        """Setup test logger"""
        self.logger = get_logger('test_logger')

    def test_logger_creation(self):
        """Test logger can be created"""
        self.assertIsNotNone(self.logger)
        self.assertIsInstance(self.logger, logging.Logger)

    def test_logger_levels(self):
        """Test different log levels work"""
        try:
            self.logger.debug("Debug message")
            self.logger.info("Info message")
            self.logger.warning("Warning message")
            self.logger.error("Error message")
            self.logger.critical("Critical message")
        except Exception as e:
            self.fail(f"Logging failed: {e}")

    def test_exception_logging(self):
        """Test exception logging with traceback"""
        try:
            raise ValueError("Test exception")
        except Exception as e:
            try:
                self.logger.error("Caught exception", exc_info=True)
            except Exception as log_error:
                self.fail(f"Exception logging failed: {log_error}")

    def test_log_exceptions_decorator(self):
        """Test @log_exceptions decorator"""

        @log_exceptions()
        def failing_function():
            raise RuntimeError("Test error")

        with self.assertRaises(RuntimeError):
            failing_function()

    def test_safe_execution_context_manager(self):
        """Test safe_execution context manager"""

        # Test with raise_on_error=False (should not raise)
        with safe_execution("test operation", self.logger, raise_on_error=False):
            raise Exception("Test exception")

        # Test with raise_on_error=True (should raise)
        with self.assertRaises(Exception):
            with safe_execution("test operation", self.logger, raise_on_error=True):
                raise Exception("Test exception")

    def test_multiple_loggers(self):
        """Test creating multiple named loggers"""
        logger1 = get_logger('module1')
        logger2 = get_logger('module2')

        self.assertIsNotNone(logger1)
        self.assertIsNotNone(logger2)
        self.assertNotEqual(logger1.name, logger2.name)


class TestLoggerIntegration(unittest.TestCase):
    """Integration tests for logger"""

    def test_logger_in_function(self):
        """Test logger usage in a function"""
        logger = get_logger('test_function')

        def test_function():
            logger.info("Function started")
            result = 42
            logger.info("Function completed")
            return result

        result = test_function()
        self.assertEqual(result, 42)

    def test_logger_with_error_handling(self):
        """Test logger with try-catch"""
        logger = get_logger('test_error_handling')

        def risky_function():
            try:
                x = 1 / 0
            except Exception as e:
                logger.error(f"Error occurred: {e}", exc_info=True)
                return None
            return 42

        result = risky_function()
        self.assertIsNone(result)


if __name__ == '__main__':
    print("Running Logger Unit Tests...")
    print("=" * 60)
    unittest.main(verbosity=2)
