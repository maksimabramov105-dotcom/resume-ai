"""
test_autoapply_linkedin.py — Module-level tests for worker/autoapply/linkedin.py.

Does NOT require a real browser or LinkedIn account.
Tests verify:
  1. The module imports successfully
  2. LinkedInApplicator class exists with the expected public interface
  3. apply() returns an error dict when Playwright is not installed
"""
import sys
from unittest.mock import patch

import pytest


def test_linkedin_module_imports():
    """The linkedin module must be importable without Playwright installed."""
    import worker.autoapply.linkedin as linkedin_module  # noqa: F401

    assert linkedin_module is not None


def test_linkedin_applicator_class_exists():
    """LinkedInApplicator must be a class with an async apply() method."""
    from worker.autoapply.linkedin import LinkedInApplicator
    import inspect

    assert inspect.isclass(LinkedInApplicator), "LinkedInApplicator should be a class"
    assert hasattr(LinkedInApplicator, "apply"), "LinkedInApplicator must have apply()"
    assert inspect.iscoroutinefunction(
        LinkedInApplicator.apply
    ), "apply() must be an async method"


@pytest.mark.asyncio
async def test_linkedin_apply_returns_error_when_playwright_not_installed():
    """
    When Playwright is not available, apply() must return a dict with
    success=False and error='playwright_not_installed' without raising.
    """
    with patch("worker.autoapply.linkedin.PLAYWRIGHT_AVAILABLE", False):
        from worker.autoapply.linkedin import LinkedInApplicator

        applicator = LinkedInApplicator()
        result = await applicator.apply(
            email="test@example.com",
            password="hunter2",
            job_title="Software Engineer",
            location="Remote",
        )

    assert isinstance(result, dict), "apply() must return a dict"
    assert result.get("success") is False
    assert result.get("error") == "playwright_not_installed"


def test_captcha_detected_error_is_exception():
    """CaptchaDetectedError must subclass Exception."""
    from worker.autoapply.linkedin import CaptchaDetectedError

    assert issubclass(CaptchaDetectedError, Exception)


def test_not_available_result_structure():
    """_not_available_result() must return the expected dict structure."""
    from worker.autoapply.linkedin import _not_available_result

    result = _not_available_result("some_func")
    assert result["success"] is False
    assert result["error"] == "playwright_not_installed"
    assert result["function"] == "some_func"
