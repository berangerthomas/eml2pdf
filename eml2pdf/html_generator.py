from __future__ import annotations

import os
import re
from datetime import datetime
from email.utils import getaddresses, parsedate_to_datetime
from xml.sax.saxutils import escape as xml_escape

from eml2pdf.parser import decode_mime_header, extract_parts


def strip_embedded_page_rules(html: str) -> str:
    """Remove embedded @page rules from imported email HTML."""
    return re.sub(r'@page\b[^{}]*\{[^{}]*\}', '', html, flags=re.IGNORECASE | re.DOTALL)


def extract_email_addresses(header_value: str) -> set[str]:
    """Return normalized email addresses extracted from a mail header value."""
    if not header_value:
        return set()

    decoded_value = decode_mime_header(header_value)
    return {
        addr.strip().lower()
        for _, addr in getaddresses([decoded_value])
        if addr.strip()
    }


def format_msg_date_label(msg, path: str) -> str:
    """Return a human-friendly date label from the message Date header or file mtime."""
    try:
        date_str = msg.get("Date")
        if date_str:
            dt = parsedate_to_datetime(date_str)
            if dt.tzinfo is not None:
                return dt.strftime("%Y-%m-%d %H:%M %z")
            return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def build_separator_html(date_label: str) -> str:
    """Generates the HTML to visually divide messages."""
    safe = xml_escape(date_label) if date_label else ""
    return (
        "<div class='separator'>"
        "<span class='sep-line'></span>"
        f"<span class='sep-date'>{safe}</span>"
        "<span class='sep-line'></span>"
        "</div>"
    )


def build_message_html(msg, headers_to_include: list[str], filename: str | None = None) -> str:
    """Generates the HTML representation of a single email message."""
    pieces = []
    if filename:
        pieces.append(f"<p class='file-label'><strong>File:</strong> {xml_escape(os.path.basename(filename))}</p>")
        
    html_parts, text_parts, attachments = extract_parts(msg)
    html_parts = [strip_embedded_page_rules(part) for part in html_parts]
    
    for h in headers_to_include:
        if h.lower() == "attachments":
            if attachments:
                att_list = ", ".join(attachments)
                pieces.append(f"<p class='header'><strong>{xml_escape(h)}:</strong> {xml_escape(att_list)}</p>")
            continue

        raw = msg.get(h)
        value = decode_mime_header(raw)
        if not value:
            continue
        pieces.append(f"<p class='header'><strong>{xml_escape(h)}:</strong> {xml_escape(value).replace('\\n','<br/>')}</p>")
        
    body_html = ""
    if html_parts:
        body_html = "\n<hr class='inner-hr'/>".join(html_parts)
    elif text_parts:
        # preserve formatting using <pre>
        joined = "\n\n".join(text_parts)
        body_html = f"<pre class='plain'>{xml_escape(joined)}</pre>"
    else:
        body_html = "<p><em>(no body)</em></p>"
        
    # Append aggressive closing tags in case the email contains unclosed tags (like <table> or <div>) that bleed and destroy layout
    body_html += "\n</div></div></div></table></table>"
        
    pieces.append(f"<div class='body'>{body_html}</div>")
    return "<div class='message'>\n" + "\n".join(pieces) + "\n</div>"


def apply_image_constraints(html: str, max_image_height: int = 800, no_images: bool = False) -> str:
    """Modifies HTML elements to enforce image size restrictions or removal."""
    # Convert width/height attributes on image-like tags into inline styles
    try:
        pattern_wh = re.compile(r'<(?P<tag>img|svg|picture|object|embed|iframe)\b(?P<attrs>[^>]*)>', flags=re.IGNORECASE)

        def _convert_wh(m):
            tag = m.group('tag')
            attrs = m.group('attrs')
            w_match = re.search(r'\bwidth\s*=\s*(?P<q>["\']?)(?P<val>\d+)(?P=q)', attrs, flags=re.IGNORECASE)
            h_match = re.search(r'\bheight\s*=\s*(?P<q>["\']?)(?P<val>\d+)(?P=q)', attrs, flags=re.IGNORECASE)
            w = w_match.group('val') if w_match else None
            h = h_match.group('val') if h_match else None
            # remove width/height attributes
            new_attrs = re.sub(r'\s(?:width|height)\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^>\s]+)', '', attrs, flags=re.IGNORECASE)
            
            style_match = re.search(r'style\s*=\s*(?P<q>["\'])(?P<content>.*?)(?P=q)', new_attrs, flags=re.IGNORECASE | re.DOTALL)
            style_parts = []
            if w:
                style_parts.append(f'width:{w}px !important')
                style_parts.append(f'max-width:{w}px !important')
            if h:
                if not w:
                    style_parts.append(f'height:{h}px !important')
                style_parts.append(f'max-height:{h}px !important')
                
            inline_css = '; '.join(style_parts)
            if style_match:
                q = style_match.group('q')
                existing = style_match.group('content')
                if inline_css and inline_css not in existing:
                    new_style = existing.rstrip('; ') + '; ' + inline_css
                    new_attrs = new_attrs[:style_match.start()] + f'style={q}{new_style}{q}' + new_attrs[style_match.end():]
            else:
                if inline_css:
                    new_attrs = new_attrs + f' style="{inline_css}"'
            return f'<{tag}{new_attrs}>'

        html = pattern_wh.sub(_convert_wh, html)
    except Exception:
        pass

    # Enforce constraints via inline injection
    inject_css = ""
    if no_images:
        inject_css = "display:none !important;"
    else:
        if max_image_height > 0:
            inject_css = f"max-width:100% !important; height:auto !important; max-height:{max_image_height}px !important;"
        else:
            inject_css = "max-width:100% !important; height:auto !important;"
            
    def _enforce_constraints(source_html: str, css: str) -> str:
        if not css: return source_html
        pattern = re.compile(r'<(img|svg|picture|object|embed|iframe)(\b[^>]*)>', flags=re.IGNORECASE)

        def repl(m):
            tag = m.group(0)
            attrs = m.group(2)
            style_match = re.search(r'style\s*=\s*(?P<q>"|\')(.*?)(?P=q)', attrs, flags=re.IGNORECASE | re.DOTALL)
            if style_match:
                q = style_match.group('q')
                existing = style_match.group(2)
                if css in existing: return tag
                new_style = existing.rstrip('; ') + '; ' + css
                new_attrs = attrs[:style_match.start()] + f'style={q}{new_style}{q}' + attrs[style_match.end():]
                return f'<{m.group(1)}{new_attrs}>'
            else:
                return f'<{m.group(1)}{attrs} style="{css}">' 

        return pattern.sub(repl, source_html)
        
    html = _enforce_constraints(html, inject_css)

    # Aggressive stripping if strictly avoiding images
    if no_images:
        html = re.sub(r'(?i)<img\b[^>]*>', '', html)
        html = re.sub(r'(?is)<svg\b.*?</svg>', '', html)
        html = re.sub(r'(?is)<object\b.*?</object>', '', html)
        html = re.sub(r'(?is)<embed\b.*?</embed>', '', html)
        html = re.sub(r'(?i)background-image\s*:\s*url\([^)]*\)\s*;?', '', html)
        html = re.sub(r'(?i)background\s*:\s*url\([^)]*\)\s*;?', '', html)
        html = re.sub(r'(?i)url\([^)]*\)', 'none', html)
        
    return html


def build_document_html(msgs: list[dict], headers: list[str], args) -> str:
    """Build the full HTML output combining multiple parsed EML messages."""
    
    font_face_css = ""
    font_apply_css = ""
    if getattr(args, "font", None):
        if os.path.exists(args.font):
            font_path = os.path.abspath(args.font).replace("\\", "/")
            font_face_css = f"@font-face {{ font-family: CustomFont; src: url('file:///{font_path}'); }}"
            font_apply_css = "body { font-family: CustomFont, Arial, Helvetica, sans-serif; }"
        else:
            pass # We could log a warning here if logging was imported at the top

    try:
        max_h = int(getattr(args, "max_image_height", 800))
    except Exception:
        max_h = 800
        
    no_images = getattr(args, "no_images", False)
    image_css = ""
    if no_images:
        image_css = (
            "img, svg, picture, object, embed, iframe { display: none !important; }"
            " *[style*='background'], [style*='background-image'] { background-image: none !important; background: none !important; }"
        )
    elif max_h and max_h > 0:
        image_css = (
            f"img, svg, picture, object, embed, iframe {{ max-width: 100% !important; width: auto !important; height: auto !important; max-height: {max_h}px !important; }}"
            " *[style*='background'], [style*='background-image'] { background-size: contain !important; background-repeat: no-repeat !important; background-position: center !important; }"
        )

    page_css = ""
    pagesize = getattr(args, "pagesize", None)
    if pagesize:
        page_css = f"@page {{ size: {pagesize}; }}"

    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html><head><meta charset='utf-8'/>")
    html.append("<style>")
    html.append(font_face_css)
    html.append(image_css)
    html.append(page_css)
    html.append("""body { font-family: Arial, Helvetica, sans-serif; font-size:12px; color:#222; }
* { max-width: 100% !important; box-sizing: border-box !important; overflow-wrap: break-word !important; word-wrap: break-word !important; word-break: break-all !important; white-space: normal !important; }
table { table-layout: fixed !important; width: 100% !important; border-collapse: collapse !important; }
td, th { overflow-wrap: break-word !important; word-wrap: break-word !important; word-break: break-all !important; }
pre, code { white-space: pre-wrap !important; word-break: break-all !important; }
.message { clear: both !important; max-width: 100% !important; overflow: hidden !important; }
.separator { text-align:center; margin:18px 0; clear: both; }
.separator .sep-line { display:inline-block; vertical-align:middle; width:32%; border-top:3px solid #444; margin:0 8px; }
.separator .sep-date { display:inline-block; vertical-align:middle; padding:6px 10px; background:#f5f5f5; border:1px solid #ddd; border-radius:4px; font-size:10px; color:#222; font-weight:600; }
.file-label { font-size:11px; margin:6px 0; font-weight:bold; }
.header { font-size:10px; margin:2px 0; color:#333; }
.body { margin-top:6px; margin-bottom:6px; }
hr { border: none; border-top: 1px solid #ccc; margin:12px 0; }
.inner-hr { border: none; border-top: 1px dashed #ddd; margin:8px 0; }
pre.plain { white-space: pre-wrap; font-family: monospace; background:#f8f8f8; padding:8px; border-radius:3px; }
.doc-summary { font-size:14px; margin-bottom:20px; padding:15px; background:#f9f9f9; border:1px solid #e0e0e0; border-radius:5px; }
.doc-summary h2 { margin-top:0; font-size:18px; }
.page-break { page-break-after: always; }""")
    html.append("</style></head><body>")

    # Inject summary if requested
    if getattr(args, "summary", False) and msgs:
        senders = set()
        recipients = set()
        timestamps = []
        for m in msgs:
            msg_obj = m["msg"]
            senders.update(extract_email_addresses(msg_obj.get("From", "")))
            recipients.update(extract_email_addresses(msg_obj.get("To", "")))
            if m.get("ts"):
                timestamps.append(m["ts"])

        min_date_str = "N/A"
        max_date_str = "N/A"
        if timestamps:
            min_ts = min(timestamps)
            max_ts = max(timestamps)
            min_date_str = datetime.fromtimestamp(min_ts).strftime("%Y-%m-%d %H:%M")
            max_date_str = datetime.fromtimestamp(max_ts).strftime("%Y-%m-%d %H:%M")

        summary_html = f'''<div class="doc-summary">
    <h2>Document Summary</h2>
    <p><strong>Total Emails:</strong> {len(msgs)}</p>
    <p><strong>Unique Senders:</strong> {len(senders)}</p>
    <p><strong>Unique Recipients:</strong> {len(recipients)}</p>
    <p><strong>Date Range:</strong> {min_date_str} to {max_date_str}</p>
</div>
<div class="page-break"></div>'''
        html.append(summary_html)

    # Add a top separator showing date of the first message
    if msgs:
        first_label = format_msg_date_label(msgs[0]["msg"], msgs[0]["path"])
        html.append(build_separator_html(first_label))

    for idx, entry in enumerate(msgs):
        html.append(build_message_html(entry["msg"], headers, filename=entry["path"]))
        if idx != len(msgs) - 1:
            # Build a visible separator that shows the date of the following message
            next_entry = msgs[idx + 1]
            date_label = format_msg_date_label(next_entry["msg"], next_entry["path"])
            html.append(build_separator_html(date_label))

    # If a custom font was provided, append a final override stylesheet
    # after all message HTML so it takes precedence over embedded email styles.
    if font_apply_css:
        override_css = (
            "body, body * { font-family: CustomFont, Arial, Helvetica, sans-serif !important; }"
            " pre.plain, code, kbd, samp, tt { font-family: monospace !important; }"
        )
        html.append(f"<style>{override_css}</style>")

    html.append("</body></html>")
    full_html = "\n".join(html)

    return apply_image_constraints(full_html, max_image_height=max_h, no_images=no_images)
