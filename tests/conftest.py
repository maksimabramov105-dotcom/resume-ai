"""
conftest.py — pytest configuration for AutoApply test suite.
Async tests use pytest-asyncio (asyncio_mode=auto set in pytest.ini).
End-to-end tests that require a live server are in end_to_end_test.py
and are excluded from CI via --ignore.
"""
