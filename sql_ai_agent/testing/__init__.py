"""
SQL AI Agent Testing Framework

A comprehensive testing suite for evaluating SQL AI Agent performance across different LLM models.

Modules:
- test_cases: Predefined test questions with expected outcomes
- framework: Main testing orchestration and execution
- debug_tester: Debug/retry mechanism testing
- reporter: CSV report generation
"""

from .test_cases import get_test_cases
from .framework import TestRunner
from .debug_tester import DebugTester

__all__ = ['get_test_cases', 'TestRunner', 'DebugTester']
