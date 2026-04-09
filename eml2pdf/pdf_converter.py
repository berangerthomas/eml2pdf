import os
import shutil
import subprocess
import tempfile
import logging


def convert_html_to_pdf(source_html: str, output_filename: str) -> bool:
    """Use the Python weasyprint library to convert HTML to PDF."""
    try:
        # import locally to avoid requiring the Python lib when using the external binary
        from weasyprint import HTML  # type: ignore
    except Exception as e:
        logging.warning("WeasyPrint Python library not available: %s", e)
        return False
        
    try:
        # Use current working directory as base_url so relative resources resolve
        base = os.getcwd()
        HTML(string=source_html, base_url=base).write_pdf(output_filename)
        return True
    except Exception as e:
        logging.warning("Failed creating PDF natively: %s", e)
        return False


def convert_html_with_binary(source_html: str, output_filename: str, bin_path: str | None = None) -> bool:
    """Write HTML to a temporary file and call an external weasyprint binary to render PDF."""
    # Search candidates: explicit path, env var, local bin/, then PATH
    candidates = []
    if bin_path:
        candidates.append(bin_path)
        
    env_bin = os.environ.get("WEASYPRINT_BIN")
    if env_bin:
        candidates.append(env_bin)
        
    candidates.append(os.path.join(os.getcwd(), "bin", "weasyprint.exe"))
    candidates.append(os.path.join(os.getcwd(), "bin", "weasyprint"))
    
    which_bin = shutil.which("weasyprint")
    if which_bin:
        # Avoid using the broken python wrapper in the current venv if possible
        candidates.append(which_bin)

    weasy_bin = None
    for c in candidates:
        if not c:
            continue
        if shutil.which(c) or os.path.exists(c):
            weasy_bin = c
            break

    if not weasy_bin:
        logging.error("WeasyPrint binary not found (searched candidates). Provide --use-binary with path or set WEASYPRINT_BIN.")
        return False

    tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
            f.write(source_html)
            tmp = f.name
        logging.info("Calling WeasyPrint binary: %s %s %s", weasy_bin, tmp, output_filename)
        cp = subprocess.run([weasy_bin, tmp, output_filename], capture_output=True, text=True)
        if cp.returncode != 0:
            logging.error("WeasyPrint binary failed: %s", cp.stderr or cp.stdout)
            return False
        return True
    except Exception as e:
        logging.error("Failed to call WeasyPrint binary: %s", e)
        return False
    finally:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def generate_pdf(html: str, output_filename: str, use_binary: str | None = None) -> bool:
    """Entry point for PDF generation router."""
    if use_binary:
        return convert_html_with_binary(html, output_filename, use_binary)
    
    if convert_html_to_pdf(html, output_filename):
        return True
        
    logging.info("Falling back to external WeasyPrint binary...")
    return convert_html_with_binary(html, output_filename)
