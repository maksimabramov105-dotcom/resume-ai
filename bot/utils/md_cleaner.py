"""Convert markdown to clean Telegram HTML. Strips ## headers, formats bold, etc."""
import re

def md_to_telegram(text: str) -> str:
    """Convert GPT markdown output to clean Telegram-safe HTML."""
    lines = []
    for line in text.split('\n'):
        # ## Header → <b>HEADER</b>
        m = re.match(r'^#{1,3}\s+(.+)', line)
        if m:
            lines.append(f"\n<b>{m.group(1).upper()}</b>")
            continue
        # **bold** → <b>bold</b>
        line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        # *italic* → <i>italic</i>
        line = re.sub(r'\*(.+?)\*', r'<i>\1</i>', line)
        # — strip lone # that slipped through
        line = re.sub(r'^#+\s*', '', line)
        lines.append(line)
    return '\n'.join(lines).strip()
