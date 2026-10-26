# Q-BE Casino Deportes — PDF Compiler Engine (src/reporting/compiler.py)
"""
Compilador de Reportes Financieros en PDF (Playwright + Jinja2).
[LN-QBE-080] [ARCH-PILLAR]
Renderiza el payload consolidado en HTML y compila el documento institucional A4
garantizando invarianza visual y maquetación anti-cortes.
"""

import re
from pathlib import Path
from jinja2 import Template
from playwright.sync_api import sync_playwright


class PDFCompilerEngine:
    @staticmethod
    def get_template() -> Template:
        template_path = Path(__file__).resolve().parent / "templates" / "master_report.html"
        if not template_path.exists():
            raise FileNotFoundError(f"No se encontró la plantilla en {template_path}")
        with open(template_path, "r", encoding="utf-8") as f:
            return Template(f.read())

    @classmethod
    def compile(cls, payload: dict, output_pdf_path: Path) -> Path:
        """
        Compila el PDF oficial en formato A4 aplicando la hoja de estilos de impresión.
        """
        template = cls.get_template()
        html_rendered = template.render(**payload)

        output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_rendered, wait_until="networkidle")
            page.pdf(
                path=str(output_pdf_path),
                format="A4",
                print_background=True,
                margin={"top": "12mm", "bottom": "14mm", "left": "12mm", "right": "12mm"},
                display_header_footer=False
            )
            browser.close()

        return output_pdf_path

    @staticmethod
    def format_filename(metadata: dict) -> str:
        """
        Genera el nombre canónico del PDF institucional sanitizando caracteres especiales.
        """
        torneo_raw = str(metadata.get("torneo", "Liga MX - Torneo Apertura 2026"))
        jornada_raw = str(metadata.get("jornada", "Jornada 7"))
        fechas_raw = str(metadata.get("fechas", "05 de Septiembre de 2026"))

        num_jornada = re.search(r"\d+", jornada_raw)
        jornada_tag = f"J{num_jornada.group(0)}" if num_jornada else jornada_raw

        if "Liga MX" in torneo_raw:
            sub_torneo = re.sub(r"^Liga\s*MX\s*[:\-\/]?\s*", "", torneo_raw).strip()
            if not sub_torneo.startswith("Torneo"):
                sub_torneo = f"Torneo {sub_torneo}"
            torneo_formateado = f"Liga MX - {sub_torneo}"
        else:
            torneo_formateado = torneo_raw

        fechas_limpias = fechas_raw.replace("Fechas:", "").strip()
        metadata["torneo_display"] = torneo_formateado
        metadata["jornada_display"] = f"Jornada {num_jornada.group(0)}" if num_jornada else jornada_raw

        nombre_pdf = f"Portafolio QBE - {torneo_formateado} {jornada_tag} - {fechas_limpias}.pdf"
        return re.sub(r"\s+", " ", nombre_pdf)


# Alias para retrocompatibilidad total
ReportCompiler = PDFCompilerEngine