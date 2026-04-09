from __future__ import annotations

import os
from email import policy
from email.parser import BytesParser
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime


def decode_mime_header(value: str) -> str:
    """Decode a MIME header value to a raw string."""
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for part, enc in parts:
        if isinstance(part, bytes):
            try:
                out.append(part.decode(enc or "utf-8", errors="replace"))
            except Exception:
                out.append(part.decode("utf-8", errors="replace"))
        else:
            out.append(part)
    return "".join(out)


def extract_parts(msg):
    """
    Extract HTML and Text parts, as well as attachment filenames, from the given email message object.
    Prioritizes parts directly under multipart or single msg.
    """
    html_parts = []
    text_parts = []
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            filename = part.get_filename()
            if filename:
                safe_name = decode_mime_header(filename)
                if safe_name not in attachments:
                    attachments.append(safe_name)
                    
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp.lower():
                continue
            if ctype == "text/html":
                try:
                    html_parts.append(part.get_content())
                except Exception:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        html_parts.append(payload.decode(charset, errors="replace"))
            elif ctype == "text/plain":
                try:
                    text_parts.append(part.get_content())
                except Exception:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        text_parts.append(payload.decode(charset, errors="replace"))
    else:
        filename = msg.get_filename()
        if filename:
            safe_name = decode_mime_header(filename)
            if safe_name not in attachments:
                attachments.append(safe_name)
                
        disp = str(msg.get("Content-Disposition", ""))
        ctype = msg.get_content_type()
        if "attachment" not in disp.lower():
            if ctype == "text/html":
                try:
                    html_parts.append(msg.get_content())
                except Exception:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or "utf-8"
                        html_parts.append(payload.decode(charset, errors="replace"))
            elif ctype == "text/plain":
                try:
                    text_parts.append(msg.get_content())
                except Exception:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or "utf-8"
                        text_parts.append(payload.decode(charset, errors="replace"))
    return html_parts, text_parts, attachments


def get_msg_timestamp(msg, path: str) -> float:
    """Return a sortable timestamp based on the message Date or file mtime."""
    try:
        date_str = msg.get("Date")
        if date_str:
            dt = parsedate_to_datetime(date_str)
            try:
                return dt.timestamp()
            except Exception:
                return datetime.now().timestamp()
    except Exception:
        pass
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0.0


def parse_eml_file(path: str) -> dict:
    """
    Parse an EML file located at the specified path and return an object structure.
    """
    with open(path, "rb") as f:
        msg = BytesParser(policy=policy.default).parse(f)

    ts = get_msg_timestamp(msg, path)
    return {
        "path": path,
        "msg": msg,
        "ts": ts
    }
