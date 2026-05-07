"""
Tests for autoapply/country_gate.py

Run: pytest autoapply/tests/test_country_gate.py -v
"""
import importlib
import sys
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — reload module with patched config so env vars don't bleed across
# ---------------------------------------------------------------------------

def _gate(blocklist=("RU", "BY"), strict=True):
    """Import country_gate with a fresh module state using the given config."""
    # Patch config values before importing
    with patch.dict("sys.modules", {}):
        # Ensure a clean import each time
        if "autoapply.country_gate" in sys.modules:
            del sys.modules["autoapply.country_gate"]

        with (
            patch("autoapply.config.COUNTRY_BLOCKLIST", frozenset(blocklist)),
            patch("autoapply.config.STRICT_DOMICILE", strict),
        ):
            import autoapply.country_gate as cg
            # Re-bind module-level references so patched values are used
            cg.COUNTRY_BLOCKLIST = frozenset(blocklist)
            cg.STRICT_DOMICILE = strict
            return cg


# ---------------------------------------------------------------------------
# resolve_company_country — explicit field
# ---------------------------------------------------------------------------

class TestResolveExplicitField:
    def test_explicit_ru(self):
        from autoapply.country_gate import resolve_company_country
        v = {"company_country": "RU", "url": "https://example.com/job"}
        assert resolve_company_country(v) == "RU"

    def test_explicit_us_overrides_tld(self):
        from autoapply.country_gate import resolve_company_country
        v = {"company_country": "us", "url": "https://company.ru/job"}
        assert resolve_company_country(v) == "US"

    def test_explicit_truncated_to_two_chars(self):
        from autoapply.country_gate import resolve_company_country
        v = {"company_country": "RUS"}  # non-standard but tolerable
        assert resolve_company_country(v) == "RU"


# ---------------------------------------------------------------------------
# resolve_company_country — TLD fallback (audit: "missing field falls back to domain")
# ---------------------------------------------------------------------------

class TestResolveTLD:
    def test_ru_domain_resolves_ru(self):
        from autoapply.country_gate import resolve_company_country
        v = {"apply_url": "https://company.ru/careers/123"}
        assert resolve_company_country(v) == "RU"

    def test_com_domain_resolves_intl(self):
        from autoapply.country_gate import resolve_company_country
        v = {"apply_url": "https://company.com/careers/123"}
        assert resolve_company_country(v) == "INTL"

    def test_by_domain_resolves_by(self):
        from autoapply.country_gate import resolve_company_country
        v = {"url": "https://company.by/job"}
        assert resolve_company_country(v) == "BY"

    def test_apply_url_preferred_over_url(self):
        """apply_url (direct ATS link) takes priority over url (job board listing)."""
        from autoapply.country_gate import resolve_company_country
        v = {
            "url":       "https://adzuna.com/redirect/123",  # job board .com
            "apply_url": "https://company.ru/apply",         # company .ru
        }
        assert resolve_company_country(v) == "RU"

    def test_io_domain_resolves_intl(self):
        from autoapply.country_gate import resolve_company_country
        v = {"apply_url": "https://myapp.io/jobs/42"}
        assert resolve_company_country(v) == "INTL"

    def test_no_url_returns_none(self):
        from autoapply.country_gate import resolve_company_country
        v = {"title": "Engineer", "company": "Acme"}
        assert resolve_company_country(v) is None

    def test_url_with_www_stripped(self):
        from autoapply.country_gate import resolve_company_country
        v = {"apply_url": "https://www.company.ru/apply"}
        assert resolve_company_country(v) == "RU"


# ---------------------------------------------------------------------------
# resolve_company_country — location keyword fallback
# ---------------------------------------------------------------------------

class TestResolveLocation:
    def test_moscow_location(self):
        from autoapply.country_gate import resolve_company_country
        v = {"location": "Moscow, Russia", "url": "https://jobs.com/123"}
        assert resolve_company_country(v) == "RU"

    def test_russia_in_location(self):
        from autoapply.country_gate import resolve_company_country
        v = {"location": "Saint Petersburg, Russia"}
        assert resolve_company_country(v) == "RU"

    def test_minsk_location(self):
        from autoapply.country_gate import resolve_company_country
        v = {"location": "Minsk, Belarus"}
        assert resolve_company_country(v) == "BY"

    def test_us_location_no_keyword_match(self):
        from autoapply.country_gate import resolve_company_country
        v = {"location": "San Francisco, CA, US", "apply_url": "https://startup.io/apply"}
        # No blocked location keyword matches → resolves via TLD
        assert resolve_company_country(v) == "INTL"


# ---------------------------------------------------------------------------
# resolve_company_country — company name fallback
# ---------------------------------------------------------------------------

class TestResolveCompanyName:
    def test_yandex_company(self):
        from autoapply.country_gate import resolve_company_country
        v = {"company": "Yandex LLC", "url": "https://jobs.com/123"}
        assert resolve_company_country(v) == "RU"

    def test_sberbank_company(self):
        from autoapply.country_gate import resolve_company_country
        v = {"company": "Sberbank Digital", "location": "Remote"}
        assert resolve_company_country(v) == "RU"

    def test_acme_company_no_match(self):
        from autoapply.country_gate import resolve_company_country
        v = {"company": "Acme Corp", "url": "https://acme.com/jobs/1"}
        assert resolve_company_country(v) == "INTL"


# ---------------------------------------------------------------------------
# is_allowed_jurisdiction — core gate logic
# ---------------------------------------------------------------------------

class TestIsAllowedJurisdiction:
    """Tests require patched config; use monkeypatch to control COUNTRY_BLOCKLIST
    and STRICT_DOMICILE without relying on environment variables."""

    def test_ru_blocked(self, monkeypatch):
        import autoapply.country_gate as cg
        monkeypatch.setattr(cg, "COUNTRY_BLOCKLIST", frozenset({"RU", "BY"}))
        monkeypatch.setattr(cg, "STRICT_DOMICILE", True)
        assert cg.is_allowed_jurisdiction("RU") is False

    def test_by_blocked(self, monkeypatch):
        import autoapply.country_gate as cg
        monkeypatch.setattr(cg, "COUNTRY_BLOCKLIST", frozenset({"RU", "BY"}))
        monkeypatch.setattr(cg, "STRICT_DOMICILE", True)
        assert cg.is_allowed_jurisdiction("BY") is False

    def test_us_allowed(self, monkeypatch):
        """US domain (or explicit US code) must pass the gate."""
        import autoapply.country_gate as cg
        monkeypatch.setattr(cg, "COUNTRY_BLOCKLIST", frozenset({"RU", "BY"}))
        monkeypatch.setattr(cg, "STRICT_DOMICILE", True)
        assert cg.is_allowed_jurisdiction("US") is True

    def test_intl_allowed(self, monkeypatch):
        """Generic international sentinel must pass the gate."""
        import autoapply.country_gate as cg
        monkeypatch.setattr(cg, "COUNTRY_BLOCKLIST", frozenset({"RU", "BY"}))
        monkeypatch.setattr(cg, "STRICT_DOMICILE", True)
        assert cg.is_allowed_jurisdiction("INTL") is True

    def test_lowercase_code_still_blocked(self, monkeypatch):
        import autoapply.country_gate as cg
        monkeypatch.setattr(cg, "COUNTRY_BLOCKLIST", frozenset({"RU", "BY"}))
        monkeypatch.setattr(cg, "STRICT_DOMICILE", True)
        assert cg.is_allowed_jurisdiction("ru") is False

    def test_none_strict_blocked(self, monkeypatch):
        """Unknown country + STRICT_DOMICILE=1 → refused (reason=unknown_jurisdiction)."""
        import autoapply.country_gate as cg
        monkeypatch.setattr(cg, "COUNTRY_BLOCKLIST", frozenset({"RU", "BY"}))
        monkeypatch.setattr(cg, "STRICT_DOMICILE", True)
        assert cg.is_allowed_jurisdiction(None) is False

    def test_none_permissive_allowed(self, monkeypatch):
        """Unknown country + STRICT_DOMICILE=0 → allowed (permissive mode)."""
        import autoapply.country_gate as cg
        monkeypatch.setattr(cg, "COUNTRY_BLOCKLIST", frozenset({"RU", "BY"}))
        monkeypatch.setattr(cg, "STRICT_DOMICILE", False)
        assert cg.is_allowed_jurisdiction(None) is True

    def test_empty_blocklist_allows_ru(self, monkeypatch):
        """With empty blocklist, even RU passes — useful in development."""
        import autoapply.country_gate as cg
        monkeypatch.setattr(cg, "COUNTRY_BLOCKLIST", frozenset())
        monkeypatch.setattr(cg, "STRICT_DOMICILE", False)
        assert cg.is_allowed_jurisdiction("RU") is True


# ---------------------------------------------------------------------------
# End-to-end gate: RU vacancy → zero applications
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_ru_domain_vacancy_is_blocked(self, monkeypatch):
        """Vacancy with a .ru apply_url must be blocked by the gate."""
        import autoapply.country_gate as cg
        monkeypatch.setattr(cg, "COUNTRY_BLOCKLIST", frozenset({"RU", "BY"}))
        monkeypatch.setattr(cg, "STRICT_DOMICILE", True)

        vacancy = {
            "id": "ru_job_1",
            "title": "Software Engineer",
            "company": "Tech Corp",
            "apply_url": "https://techcorp.ru/careers/1",
            "url": "https://techcorp.ru/careers/1",
            "location": "Moscow",
        }
        country = cg.resolve_company_country(vacancy)
        assert country == "RU"
        assert cg.is_allowed_jurisdiction(country) is False

    def test_us_com_vacancy_is_allowed(self, monkeypatch):
        """Vacancy with a .com apply_url must pass through."""
        import autoapply.country_gate as cg
        monkeypatch.setattr(cg, "COUNTRY_BLOCKLIST", frozenset({"RU", "BY"}))
        monkeypatch.setattr(cg, "STRICT_DOMICILE", True)

        vacancy = {
            "id": "us_job_1",
            "title": "Backend Engineer",
            "company": "Startup Inc",
            "apply_url": "https://startup.com/apply/42",
            "url": "https://adzuna.com/redirect/999",
            "location": "Remote",
        }
        country = cg.resolve_company_country(vacancy)
        assert country == "INTL"
        assert cg.is_allowed_jurisdiction(country) is True

    def test_unknown_country_strict_produces_no_application(self, monkeypatch, caplog):
        """Vacancy with no resolvable country + STRICT_DOMICILE=1 is blocked and logged."""
        import logging
        import autoapply.country_gate as cg
        monkeypatch.setattr(cg, "COUNTRY_BLOCKLIST", frozenset({"RU", "BY"}))
        monkeypatch.setattr(cg, "STRICT_DOMICILE", True)

        vacancy = {"id": "mystery_1", "title": "Developer", "company": "???"}
        country = cg.resolve_company_country(vacancy)
        assert country is None

        with caplog.at_level(logging.INFO, logger="autoapply.country_gate"):
            allowed = cg.is_allowed_jurisdiction(country)

        assert allowed is False
        assert "unknown_jurisdiction" in caplog.text
