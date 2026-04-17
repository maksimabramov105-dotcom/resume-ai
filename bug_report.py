#!/usr/bin/env python3
"""
bug_report.py — Global error handler and bug reporter
Import and use wrap_with_bug_report() or install_global_handler()

Usage example:

    from bug_report import wrap_with_bug_report, async_wrap_with_bug_report, install_global_handler

    # Install global uncaught exception handler (call once at startup)
    install_global_handler()

    # Decorate a sync function
    @wrap_with_bug_report
    def risky_operation():
        raise ValueError("something broke")

    # Decorate an async function
    @async_wrap_with_bug_report
    async def risky_async_operation():
        raise RuntimeError("async broke")

    # Or wrap inline
    safe_fn = wrap_with_bug_report(some_function)
"""
import asyncio
import aiohttp
import logging
import traceback
import os
import sys
from datetime import datetime
from functools import wraps

ADMIN_CHAT_ID = int(os.getenv("ADMIN_ID", "0")))
BOT_TOKEN     = os.getenv("BOT_TOKEN", "")
LOGS_DIR      = os.getenv("LOGS_DIR", "/opt/resumeaibot/logs")
ERROR_LOG     = os.path.join(LOGS_DIR, "errors.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("bug_report")


async def send_bug_alert(
    filename: str,
    line: int,
    error_msg: str,
    tb_short: str,
) -> None:
    """Send a bug alert to the admin via Telegram."""
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN not set — cannot send bug alert")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"🐛 <b>Bug Detected</b>\n"
        f"📍 File: <code>{filename}</code>  Line: <code>{line}</code>\n"
        f"❌ Error: <code>{error_msg}</code>\n"
        f"📋 {tb_short[:200]}\n"
        f"🕐 {timestamp}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    log.error("Bug alert Telegram send failed: HTTP %d — %s", resp.status, body)
    except Exception as e:
        log.error("Failed to send bug alert: %s", e)


def log_error_to_file(tb_full: str) -> None:
    """Append a full traceback with timestamp to the error log file."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    separator = "=" * 70
    entry = f"\n{separator}\n[{timestamp}]\n{tb_full}\n"
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        log.error("Failed to write to error log %s: %s", ERROR_LOG, e)


def _extract_error_info(exc: BaseException) -> tuple[str, int, str, str, str]:
    """Extract filename, line number, error message, short and full tracebacks."""
    tb_full = traceback.format_exc()
    tb_lines = tb_full.strip().splitlines()

    filename = "unknown"
    line = 0
    # Walk the traceback looking for the innermost file reference
    for tb_line in tb_lines:
        stripped = tb_line.strip()
        if stripped.startswith("File "):
            parts = stripped.split(",")
            if len(parts) >= 2:
                try:
                    filename = parts[0].replace('File "', "").replace('"', "").strip()
                    line = int(parts[1].strip().replace("line ", ""))
                except (ValueError, IndexError):
                    pass

    error_msg = f"{type(exc).__name__}: {exc}"
    tb_short = "\n".join(tb_lines[-6:]) if len(tb_lines) > 6 else tb_full
    return filename, line, error_msg, tb_short, tb_full


def wrap_with_bug_report(func):
    """
    Decorator for synchronous functions.
    Catches all exceptions, logs them to file, sends Telegram alert, then re-raises.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            filename, line, error_msg, tb_short, tb_full = _extract_error_info(exc)
            log.error("Bug in %s: %s", func.__qualname__, error_msg)
            log_error_to_file(tb_full)
            # Fire-and-forget alert in a new event loop (sync context)
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(send_bug_alert(filename, line, error_msg, tb_short))
                loop.close()
            except Exception as alert_err:
                log.error("Could not send bug alert: %s", alert_err)
            raise
    return wrapper


def async_wrap_with_bug_report(func):
    """
    Decorator for async functions.
    Catches all exceptions, logs them to file, sends Telegram alert, then re-raises.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            filename, line, error_msg, tb_short, tb_full = _extract_error_info(exc)
            log.error("Bug in %s: %s", func.__qualname__, error_msg)
            log_error_to_file(tb_full)
            try:
                await send_bug_alert(filename, line, error_msg, tb_short)
            except Exception as alert_err:
                log.error("Could not send bug alert: %s", alert_err)
            raise
    return wrapper


def install_global_handler() -> None:
    """
    Install global exception handlers:
    - sys.excepthook for synchronous uncaught exceptions
    - asyncio exception handler for uncaught async exceptions

    Call once at application startup (e.g., top of bot.py or main.py).
    """

    def _sync_excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't report Ctrl+C
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        tb_full = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        filename, line, error_msg, tb_short, _ = _extract_error_info(exc_value)

        log.critical("Uncaught exception: %s", error_msg)
        log_error_to_file(tb_full)

        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(send_bug_alert(filename, line, error_msg, tb_short))
            loop.close()
        except Exception as e:
            log.error("Could not send global exception alert: %s", e)

        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _sync_excepthook

    def _async_exception_handler(loop, context):
        exc = context.get("exception")
        if exc is None:
            msg = context.get("message", "Unknown async error")
            log.error("Async error (no exception object): %s", msg)
            return

        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            return

        tb_full = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        filename, line, error_msg, tb_short, _ = _extract_error_info(exc)

        log.critical("Uncaught async exception: %s", error_msg)
        log_error_to_file(tb_full)

        asyncio.ensure_future(
            send_bug_alert(filename, line, error_msg, tb_short),
            loop=loop,
        )

    try:
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(_async_exception_handler)
        log.info("Global bug report handlers installed (sync + async)")
    except RuntimeError:
        # No running event loop yet — will be set when loop starts
        log.info("Global sync bug report handler installed (async handler pending loop)")
