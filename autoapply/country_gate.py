"""
country_gate.py — Company jurisdiction filter for AutoApply.

Public API:
  resolve_company_country(vacancy: dict) -> str | None
  is_allowed_jurisdiction(country_code: str | None) -> bool

Both functions are pure (no I/O) to keep them cheaply unit-testable.
"""
import logging
from urllib.parse import urlparse

from autoapply.config import COUNTRY_BLOCKLIST, STRICT_DOMICILE

logger = logging.getLogger(__name__)

# ── TLD → ISO-3166-1 alpha-2 (or sentinel) ────────────────────────────────────
#
# "INTL" = generic international TLD — not country-specific, not blocked.
# Country-code TLDs map to their ISO code.
# None = unknown / can't determine.
#
_TLD_MAP: dict[str, str | None] = {
    # Blocked ccTLDs
    "ru":   "RU",
    "рф":   "RU",   # Cyrillic IDN for Russia
    "рус":  "RU",
    "by":   "BY",
    "бел":  "BY",   # Cyrillic IDN for Belarus
    # International generic TLDs — clearly not Russia-specific
    "com":  "INTL",
    "org":  "INTL",
    "net":  "INTL",
    "io":   "INTL",
    "co":   "INTL",
    "ai":   "INTL",
    "app":  "INTL",
    "dev":  "INTL",
    "tech": "INTL",
    "jobs": "INTL",
    "work": "INTL",
    "careers": "INTL",
    # Country ccTLDs (allowed — just for completeness)
    "us":   "US",
    "uk":   "GB",
    "gb":   "GB",
    "de":   "DE",
    "fr":   "FR",
    "nl":   "NL",
    "ca":   "CA",
    "au":   "AU",
    "nz":   "NZ",
    "sg":   "SG",
    "in":   "IN",
    "fi":   "FI",
    "se":   "SE",
    "no":   "NO",
    "dk":   "DK",
    "pl":   "PL",
    "cz":   "CZ",
    "es":   "ES",
    "pt":   "PT",
    "it":   "IT",
    "at":   "AT",
    "ch":   "CH",
    "be":   "BE",
    "ie":   "IE",
    "ee":   "EE",
    "lv":   "LV",
    "lt":   "LT",
    "hu":   "HU",
    "ro":   "RO",
    "sk":   "SK",
    "si":   "SI",
    "hr":   "HR",
    "bg":   "BG",
    "gr":   "GR",
    "tr":   "TR",
    "il":   "IL",
    "ae":   "AE",
    "jp":   "JP",
    "kr":   "KR",
    "br":   "BR",
    "mx":   "MX",
    "ar":   "AR",
    "cl":   "CL",
    "za":   "ZA",
    "ng":   "NG",
    "ke":   "KE",
}

# Location substrings that imply a blocked jurisdiction (lowercase comparison)
_BLOCKED_LOCATION: dict[str, str] = {
    "russia":            "RU",
    "москва":            "RU",
    "moscow":            "RU",
    "санкт-петербург":   "RU",
    "saint petersburg":  "RU",
    "st. petersburg":    "RU",
    "novosibirsk":       "RU",
    "yekaterinburg":     "RU",
    "ekaterinburg":      "RU",
    "kazan":             "RU",
    "russian federation":"RU",
    "belarus":           "BY",
    "belorussia":        "BY",
    "minsk":             "BY",
    "минск":             "BY",
    "беларусь":          "BY",
}

# Company name substrings that strongly indicate a Russian/Belarusian company.
# Used only as a last-resort heuristic — all entries map to "RU" or "BY".
_BLOCKED_COMPANY: dict[str, str] = {
    "сбер":        "RU",
    "sberbank":    "RU",
    "yandex":      "RU",
    "яндекс":      "RU",
    "mail.ru":     "RU",
    "vkontakte":   "RU",
    "газпром":     "RU",
    "gazprom":     "RU",
    "росатом":     "RU",
    "rosatom":     "RU",
    "лукойл":      "RU",
    "lukoil":      "RU",
    "ростелеком":  "RU",
    "rostelecom":  "RU",
    "мтс":         "RU",
    "hh.ru":       "RU",
    "авито":       "RU",
    "avito.ru":    "RU",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _tld_from_url(url: str) -> str | None:
    """Return the rightmost label of the hostname (lowercased), or None."""
    if not url:
        return None
    try:
        host = urlparse(url).hostname or ""
        host = host.lower().lstrip("www.")
        parts = host.rsplit(".", 1)
        if len(parts) == 2 and parts[1]:
            return parts[1]
    except Exception:
        pass
    return None


# ── Public API ─────────────────────────────────────────────────────────────────

def resolve_company_country(vacancy: dict) -> str | None:
    """
    Heuristic to determine a vacancy's company country (ISO-3166-1 alpha-2).

    Resolution priority:
      1. Explicit ``company_country`` field on the vacancy dict.
      2. TLD of ``apply_url`` / ``url``.  A specific country TLD (e.g. ``.ru``)
         is a *strong* signal and returned immediately.  A generic international
         TLD (e.g. ``.com``) is *weak*: we note it and continue so location/
         company heuristics can override it.
      3. Location string keyword match.
      4. Company name substring match.
      5. ``"INTL"`` if only a generic TLD was found and no stronger signal.
      6. ``None`` when the country cannot be determined at all.
    """
    # 1. Explicit field
    explicit = vacancy.get("company_country")
    if explicit:
        return str(explicit).upper()[:2]

    # 2. TLD scan — strong country codes returned immediately; "INTL" noted and
    #    deferred so heuristics 3-4 can override (location > generic TLD).
    tld_gave_intl = False
    for url_key in ("apply_url", "url"):
        tld = _tld_from_url(vacancy.get(url_key, ""))
        if not tld or tld not in _TLD_MAP:
            continue
        mapped = _TLD_MAP[tld]
        if mapped == "INTL":
            tld_gave_intl = True
            break  # weak signal — fall through to stronger heuristics
        if mapped is not None:
            return mapped  # specific country code (e.g. "RU") — return now

    # 3. Location keywords
    location = (vacancy.get("location") or "").lower()
    for keyword, code in _BLOCKED_LOCATION.items():
        if keyword in location:
            logger.debug("[country_gate] location heuristic: %r → %s", keyword, code)
            return code

    # 4. Company name keywords
    company = (vacancy.get("company") or "").lower()
    for keyword, code in _BLOCKED_COMPANY.items():
        if keyword in company:
            logger.debug("[country_gate] company name heuristic: %r → %s", keyword, code)
            return code

    # 5. If a generic TLD was the only signal and nothing stronger was found
    if tld_gave_intl:
        return "INTL"

    return None


def is_allowed_jurisdiction(country_code: str | None) -> bool:
    """
    Return True if applications to this company are allowed.

    Blocking rules (checked in order):
      1. ``country_code`` is None and ``STRICT_DOMICILE=1`` → blocked.
      2. ``country_code`` (uppercased) is in ``COUNTRY_BLOCKLIST`` → blocked.
      3. Otherwise → allowed.
    """
    if country_code is None:
        if STRICT_DOMICILE:
            logger.info(
                "[country_gate] blocked: country unknown, STRICT_DOMICILE=1 "
                "(reason=unknown_jurisdiction)"
            )
            return False
        return True

    code = country_code.upper()
    if code in COUNTRY_BLOCKLIST:
        logger.info("[country_gate] blocked: country=%s in COUNTRY_BLOCKLIST", code)
        return False

    return True
