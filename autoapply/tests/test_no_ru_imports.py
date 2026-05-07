"""
Guard test: ensure no Russian job board modules are imported by the autoapply package.

Adding hh_scraper or superjob_scraper back must break this test.
"""
import importlib
import pkgutil
import sys


def _collect_autoapply_modules() -> list[str]:
    """Return names of all modules currently loaded that belong to autoapply."""
    return [name for name in sys.modules if name == "autoapply" or name.startswith("autoapply.")]


def test_no_hh_module_imported():
    """Importing autoapply must not pull in any hh-related module."""
    import autoapply  # noqa: F401 — triggers package __init__
    loaded = _collect_autoapply_modules()
    ru_modules = [m for m in loaded if "hh" in m.lower()]
    assert not ru_modules, (
        f"Russian job board module(s) found after importing autoapply: {ru_modules}. "
        "Remove hh_scraper / headhunter imports from the package."
    )


def test_no_superjob_module_imported():
    """Importing autoapply must not pull in any superjob-related module."""
    import autoapply  # noqa: F401
    loaded = _collect_autoapply_modules()
    ru_modules = [m for m in loaded if "superjob" in m.lower()]
    assert not ru_modules, (
        f"Russian job board module(s) found after importing autoapply: {ru_modules}. "
        "Remove superjob_scraper imports from the package."
    )


def test_no_zarplata_module_imported():
    """Importing autoapply must not pull in any zarplata-related module."""
    import autoapply  # noqa: F401
    loaded = _collect_autoapply_modules()
    ru_modules = [m for m in loaded if "zarplata" in m.lower()]
    assert not ru_modules, (
        f"Russian job board module(s) found after importing autoapply: {ru_modules}. "
        "Remove zarplata imports from the package."
    )
