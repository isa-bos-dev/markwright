# Changelog

All notable changes to Markwright are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- **The desktop GUI is parked** on the `gui-desktop` branch (untouched, not
  actively maintained), in favor of focusing on conversion fidelity and a solid
  CLI — see `docs/constitution.md`'s Purpose section for the full reasoning.
  Running `markwright` with no arguments now opens the interactive menu (the
  GUI's old role as the effortless entry point), instead of a graphical window.
- `markwright menu`'s Help option now shows the CLI's own `--help` text in
  place, instead of pointing you to a command you can't run from inside the
  already-running menu.

### Removed

- Persistent GUI settings (language/theme/font size) and the `sv-ttk` dependency
  — both were GUI-only.

## [0.2.0] - 2026-09-30

### Added

- Persistent interface settings: language, light/dark theme and font size, saved
  in `%APPDATA%\Markwright\` and applied on every launch. The GUI no longer shows
  a language-selection screen on startup — a gear icon changes them at any time.
- Interactive terminal menu (`markwright menu`): pick a PDF from a numbered list
  of the ones in the current folder, without typing the full path.
- `--version` / `-V` flag.

### Security

- Conversions now time out after 10 minutes instead of being able to run
  indefinitely on a hostile or pathologically large PDF.
- Disabled `huggingface_hub`'s anonymous usage telemetry unconditionally, from
  the very first run (it was previously only disabled once local models had
  already been found).

## [0.1.0] - 2026-09-23

### Added

- Core PDF-to-Markdown conversion, preserving tables, lists, heading hierarchy
  and images (`docling`, EasyOCR for scanned pages).
- Command-line interface (`markwright <file.pdf>`), with localized errors,
  progress messages and exit codes.
- Graphical interface (double-click, no install required), running the
  conversion in the background so the window never freezes.
- Bilingual interface: English and Spanish.
- Password-protected PDFs, decrypted in memory.
- Original branding (logo, window/executable icon).

[Unreleased]: https://github.com/isa-bos-dev/markwright/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/isa-bos-dev/markwright/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/isa-bos-dev/markwright/releases/tag/v0.1.0
