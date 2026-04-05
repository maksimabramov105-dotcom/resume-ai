import os
from fpdf import FPDF

# Candidate paths for DejaVuSans fonts (bundled first, then OS paths)
_FONT_CANDIDATES = [
    # Bundled in project
    (
        os.path.join(os.path.dirname(__file__), '..', 'fonts', 'DejaVuSans.ttf'),
        os.path.join(os.path.dirname(__file__), '..', 'fonts', 'DejaVuSans-Bold.ttf'),
    ),
    # Linux system fonts (Ubuntu/Debian)
    (
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ),
    # macOS (Homebrew)
    (
        '/opt/homebrew/share/fonts/dejavu-fonts/DejaVuSans.ttf',
        '/opt/homebrew/share/fonts/dejavu-fonts/DejaVuSans-Bold.ttf',
    ),
]


def _find_fonts():
    """Return (regular, bold) TTF paths or (None, None) if not found."""
    for regular, bold in _FONT_CANDIDATES:
        if os.path.exists(regular) and os.path.exists(bold):
            # Quick sanity check: real TTF starts with specific magic bytes
            with open(regular, 'rb') as f:
                magic = f.read(4)
            # Valid TTF/OTF magic: 0x00010000, 'OTTO', 'true', 'typ1'
            if magic[:2] in (b'\x00\x01', b'OT', b'tr', b'ty'):
                return regular, bold
    return None, None


class ResumePDF(FPDF):
    def __init__(self):
        super().__init__()
        regular, bold = _find_fonts()

        if regular and bold:
            self.add_font('DejaVu', '', regular)
            self.add_font('DejaVu', 'B', bold)
            self._font = 'DejaVu'
        else:
            # Fallback to built-in font (no Cyrillic, but won't crash)
            self._font = 'Helvetica'

    def generate(self, resume_text: str, full_name: str) -> bytes:
        """Generate PDF from resume text. Returns bytes."""
        self.add_page()
        self.set_margins(15, 15, 15)

        # Title
        self.set_font(self._font, 'B', 18)
        self.cell(0, 12, full_name, new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(4)

        self.set_font(self._font, '', 11)
        for line in resume_text.split('\n'):
            stripped = line.strip()
            if not stripped:
                self.ln(3)
                continue

            # Section headers: lines starting with ## or all-uppercase short lines
            if stripped.startswith('##') or (stripped.isupper() and len(stripped) < 60):
                self.ln(2)
                self.set_font(self._font, 'B', 13)
                heading = stripped.lstrip('#').strip()
                self.cell(0, 8, heading, new_x="LMARGIN", new_y="NEXT")
                # Underline
                y = self.get_y()
                self.line(self.l_margin, y, self.w - self.r_margin, y)
                self.ln(2)
                self.set_font(self._font, '', 11)
            elif stripped.startswith('**') and stripped.endswith('**'):
                self.set_font(self._font, 'B', 11)
                self.multi_cell(0, 6, stripped.strip('*'))
                self.set_font(self._font, '', 11)
            else:
                self.multi_cell(0, 6, line)

        return bytes(self.output())
