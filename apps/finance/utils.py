"""
finance/utils.py
Shared helpers (PDF rendering, …) for the Finance app.
"""

import logging
from io import BytesIO

from django.template.loader import get_template
from django.conf            import settings

# Choose *one* backend.  Two common examples are shown; comment-out the
# one you’re not using.

# ── OPTION A:  WeasyPrint  ───────────────────────────────────────────
from weasyprint import HTML, CSS
#
# ── OPTION B:  xhtml2pdf  (pisa)  ───────────────────────────────────
# from xhtml2pdf import pisa

logger = logging.getLogger(__name__)


def _render_pdf(template_path: str, context: dict[str, object]) -> bytes | None:
    """
    Render *template_path* with *context* and return the resulting PDF bytes.
    Returns **None** if generation fails (caller can handle the 500).
    """

    html = get_template(template_path).render(context)

    try:
        # ───────────────────────────  WeasyPrint  ──────────────────
        pdf_bytes = HTML(
            string=html,
            base_url=settings.STATIC_ROOT or settings.BASE_DIR,
        ).write_pdf(stylesheets=[
            CSS(string="@page { size:A4; margin:18mm 15mm 20mm; }")
        ])
        return pdf_bytes

        # ───────────────────────────  xhtml2pdf  ───────────────────
        # buf = BytesIO()
        # pisa.CreatePDF(src=html, dest=buf, encoding="utf-8")
        # return buf.getvalue()
    except Exception as exc:
        logger.exception("PDF generation failed: %s", exc)
        return None

