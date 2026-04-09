import argparse
import glob
import os
import sys
import logging

from eml2pdf.parser import parse_eml_file, decode_mime_header
from eml2pdf.html_generator import build_document_html
from eml2pdf.pdf_converter import generate_pdf


def get_sort_key(sk: str, obj: dict):
    if sk.lower() in ("file", "filename", "path"):
        return obj["path"]
    elif sk.lower() in ("mtime", "filemtime"):
        return os.path.getmtime(obj["path"]) if os.path.exists(obj["path"]) else 0.0
    elif sk.lower() == "date":
        return obj["ts"] or 0.0
    
    # Header fallback
    raw = obj["msg"].get(sk)
    try:
        val = decode_mime_header(raw) if raw else ""
    except Exception:
        val = raw or ""
    return (val or "").lower()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
        
    parser = argparse.ArgumentParser(description="Convert EML files to a single PDF (render HTML bodies)")
    parser.add_argument("input", help="glob for EML files (e.g. 'emails/*.eml' or 'C:\\\\mails\\\\**\\\\*.eml' for recursive search)")
    parser.add_argument("-o", "--output", default="out.pdf", help="output PDF filename")
    parser.add_argument("-H", "--headers", default="From,To,Subject,Date", help="comma-separated header fields to include (can include 'Attachments')")
    parser.add_argument(
        "--pagesize",
        choices=["A3", "A4", "A5", "B4", "B5", "LETTER", "LEGAL", "LEDGER"],
        default="A4",
        help="page size of the generated PDF"
    )
    parser.add_argument(
        "--font",
        help=(
            "optional path to a font file (TTF/OTF/WOFF/WOFF2) to use for rendering the PDF. If omitted, system fonts are used."
        ),
    )
    
    parser.add_argument(
        "--sort-by",
        choices=["Date", "Subject", "From", "To", "file", "mtime"],
        default="Date",
        help="header field to sort messages by.",
    )
    parser.add_argument(
        "--sort-order",
        choices=["asc", "desc"],
        default="desc",
        help="sort order: 'asc' or 'desc' (default 'desc' = reverse).",
    )
    parser.add_argument(
        "--use-binary",
        help="use external weasyprint executable at BIN (provide path to binary). If omitted, uses Python weasyprint library.",
        metavar="BIN",
    )
    
    img_group = parser.add_mutually_exclusive_group()
    img_group.add_argument(
        "--no-images",
        action="store_true",
        help="hide/remove images from the rendered HTML output (mutually exclusive with --max-image-height)",
    )
    img_group.add_argument(
        "--max-image-height",
        type=int,
        default=800,
        help="maximum image height in pixels (0 = no limit) (mutually exclusive with --no-images)",
    )
    
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print a summary at the top of the PDF (number of emails, senders, recipients, date range)"
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    headers = [h.strip() for h in args.headers.split(",") if h.strip()]

    files = glob.glob(args.input, recursive=True)
    files = sorted(files)
    if not files:
        logging.error("No files found for: %s", args.input)
        sys.exit(2)

    msgs = []
    for path in files:
        try:
            msgs.append(parse_eml_file(path))
        except Exception as e:
            logging.error("Failed to parse %s: %s", path, e)
            continue

    if not msgs:
        logging.error("No valid EML messages successfully parsed. Exiting.")
        sys.exit(3)

    # Sorting
    sk = (getattr(args, "sort_by", "Date") or "Date").strip()
    order = getattr(args, "sort_order", "desc") or "desc"
    reverse = (str(order).lower() == "desc")
    
    msgs.sort(key=lambda x: get_sort_key(sk, x), reverse=reverse)

    # Document generation
    html = build_document_html(msgs, headers, args)
    
    # PDF generation
    ok = generate_pdf(html, args.output, use_binary=args.use_binary)
    if not ok:
        logging.error("PDF generation failed.")
        sys.exit(4)
        
    logging.info("Written PDF: %s", args.output)

if __name__ == "__main__":
    main()
