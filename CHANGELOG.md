# Changelog

## v0.2.0 - 2026-04-09

### Added
- Initial release of `eml2pdf`: convert a set of `.eml` files into a single PDF while preserving HTML message bodies.
- CLI accessible via the `eml2pdf` command with useful options:
	- `--sort-by` (choices: `Date`, `Subject`, `From`, `To`, `file`, `mtime`)
	- `--use-binary` (path to an external WeasyPrint executable) with a graceful fallback to the binary on Windows when native libraries are missing
	- `--summary` prints a summary block at the beginning of the PDF (number of emails, senders, recipients, date range)
	- `--pagesize` supports `A4`, `LETTER`, `A3`, `A5`, `B4`, `B5`, `LEGAL`, `LEDGER`
	- `--font` accepts common font formats (TTF/OTF/WOFF/WOFF2); if omitted, WeasyPrint uses system fonts via Pango/Fontconfig; WeasyPrint embeds and subsets fonts by default
	- `--no-images` and `--max-image-height` to control image inclusion and sizing (mutually exclusive)
- Attachment file names are extracted and can be injected into the output PDF by adding `Attachments` to the `--headers` comma-separated list.
- Reliable inline image and style handling for consistent PDF rendering.
- Embedded `@page` rules from imported email HTML are stripped before rendering to prevent messages from altering the final page size.
- Integrated standard Python `logging` for feedback and debugging.

### Notes
- Recursive glob matching is implicit; use `**` in input patterns to include subdirectories.
- Logging level is configured inside the script by design.
- README and CLI help include informations about `--font` behavior and supported formats.