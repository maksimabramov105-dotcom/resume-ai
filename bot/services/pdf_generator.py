import os
from fpdf import FPDF


class ResumePDF(FPDF):
    def __init__(self):
        super().__init__()
        font_dir = os.path.join(os.path.dirname(__file__), '..', 'fonts')
        dejavu = os.path.join(font_dir, 'DejaVuSans.ttf')
        dejavu_bold = os.path.join(font_dir, 'DejaVuSans-Bold.ttf')

        if os.path.exists(dejavu) and os.path.exists(dejavu_bold):
            self.add_font('DejaVu', '', dejavu)
            self.add_font('DejaVu', 'B', dejavu_bold)
            self._font = 'DejaVu'
        else:
            # Fallback to built-in font (no Cyrillic support)
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
