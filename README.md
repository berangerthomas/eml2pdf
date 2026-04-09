# eml2pdf

Weasyprint based Python utility to parse `.eml` files and export them into a single PDF.

## Installation

Download the application:

- Clone the repository:

```bash
git clone https://github.com/berangerthomas/eml2pdf.git
cd eml2pdf
```

Or download the ZIP from the project's GitHub page and extract it.

- Set up and install dependencies with uv :

```bash
uv sync
```

- Optional — create and activate a virtual environment first (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
uv sync
```

If you plan to use an external WeasyPrint executable on Windows, see the section [Windows — using the WeasyPrint binary](#windows-using-the-weasyprint-binary).

## Usage

Simple example: all .eml files in the mails folder :
```bash
uv run eml2pdf "emails\*.eml" -o archive.pdf -H From,To,Subject,Date
```

Sort by subject (ascending) :
```bash
uv run eml2pdf "emails\*.eml" --sort-by Subject --sort-order asc -o archive.pdf
```

With recursive glob matching (use **) :
```bash
uv run eml2pdf "archive\**\emails\*.eml" -o archive.pdf
```

Use an external WeasyPrint binary (see section [Windows](#windows-using-the-weasyprint-binary)) :
```bash
uv run eml2pdf "emails\*.eml" -o archive.pdf --use-binary "bin/weasyprint.exe"
```

Specify a font file for consistent rendering (TTF/OTF/WOFF/WOFF2 supported) (see section [Fonts](#details-about-font-use)) :
```bash
uv run eml2pdf --use-binary .\bin\weasyprint.exe .\mails\*.eml --font '.\fonts\SourceSerif4-VariableFont_opsz,wght.ttf' -o archive.pdf
```

## Primary options
- `input`: glob pattern that targets `.eml` files (quote the pattern in PowerShell). Use `**` for recursive matching.
- `-o, --output`: output PDF filename (default `out.pdf`)
- `-H, --headers`: comma-separated header fields to include (e.g. `From,To,Subject,Date`)
- `--font`: optional path to a font file (TTF/OTF/WOFF/WOFF2). If omitted, system fonts are used.
- `--sort-by`: header field used to sort messages (choices: `Date`, `Subject`, `From`, `To`, `file`, `mtime`). Default: `Date`.
- `--sort-order`: sort order `asc` or `desc` (default `desc` = reverse chronological for `Date`).
- `--use-binary BIN`: use an external WeasyPrint executable (provide path to binary). If omitted, the Python `weasyprint` library is used when available.
- `--no-images` / `--max-image-height`: these options are mutually exclusive. `--no-images` hides/removes images; `--max-image-height N` limits image height to `N` pixels (default `800`, `0` = no limit).

## Behavior and rendering
- If a message contains `text/html`, its HTML body is preserved and rendered directly into the PDF.
- Otherwise, `text/plain` is included in a preformatted block (`<pre>`) to preserve formatting.
- By default messages are sorted in reverse chronological order (header `Date`, falling back to file modification time).
- Messages are concatenated into a single HTML document separated by visible separators. Each separator displays the date of the following message.

## Images handling

#### `--no-images`
- If `--no-images` is enabled, all inline images and background images are removed from the HTML before PDF generation. In practice this:
  - injects CSS rules to hide `<img>` elements and prevent inline background images from displaying;
  - also removes `<img>`, `<svg>`, `<object>`, `<embed>` elements and strips inline `background-image`/`url()` usages to override inline `!important` styles and backgrounds defined in the HTML.

#### `--max-image-height`
- Image resizing targets multiple element types (`img`, `svg`, `picture`, `object`, `embed`, `iframe`) and attempts to override inline styles.
- The script strips certain inline attributes (`width`, `height`, `max-width`, `max-height`) so injected CSS can reliably constrain images.

## Details about font use

When exporting your emails to a PDF document, you can use the `--font` argument to specify a font of your choice.

- The open-source `Noto` font, in its serif or sans serif version, has one of the largest glyph coverages (Noto font on Google fonts : https://fonts.google.com/noto).

- If `--font` is ommited, system fonts are used. WeasyPrint uses Pango/Fontconfig to match fonts (see https://www.freedesktop.org/wiki/Software/fontconfig/ and https://pango.org/).
 
- WeasyPrint embeds and subsets fonts by default (see https://harfbuzz.github.io/harfbuzz-hb-subset.html)

## Windows - using the WeasyPrint binary

WeasyPrint's maintainers recommend using the standalone executable on Windows (see official docs) because installing native dependencies (Cairo, Pango, GDK‑PixBuf, etc.) can be cumbersome.

You can find the latest Windows binary here: https://github.com/Kozea/WeasyPrint/releases.

Just unzip the binary (`weasyprint.exe`) into a directory of your choice and launch the relevant command line:

```powershell
uv run eml2pdf "mails/*.eml" -o merged.pdf --use-binary .\bin\weasyprint.exe
```

If `--use-binary` is not provided the script searches, in order: the environment variable `WEASYPRINT_BIN`, a `weasyprint` binary on the `PATH`, then `./bin/weasyprint.exe` and `./bin/weasyprint`.
