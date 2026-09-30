# Security Policy

## Supported Versions

Markwright is pre-1.0 and under active development. Only the latest version on
`main` is supported — there is no long-term support for older releases yet.

## Reporting a Vulnerability

Please report security vulnerabilities privately through
[GitHub Private Vulnerability Reporting](https://github.com/isa-bos-dev/markwright/security/advisories/new).
**Do not open a public issue for a security concern.**

This is a single-maintainer project worked on outside full-time hours, so please
allow a few days for an initial response — every report is read and taken
seriously.

## Scope

Markwright is a local, single-user desktop application:

- It has no server component and no network-exposed API.
- It processes PDF files you choose yourself, entirely on your own machine.
- The only network traffic it makes is downloading its own ML models from their
  official sources (docling/Hugging Face, EasyOCR), the first time they are
  needed — never your documents or their content.

The most realistic threat here is a **hostile PDF file** exploiting a bug in
Markwright itself or in one of its parsing dependencies (`docling`, `pypdf`,
`easyocr`). Reports along those lines are very welcome.

## Known, Accepted Risks

Documented deliberately, not overlooked:

- **A pathologically large or malicious PDF can still slow down the conversion or
  use significant memory.** Conversions are bounded to 10 minutes, so the app
  cannot hang forever, but a very fast memory spike within that window is not
  caught yet — that would need the conversion to run in an isolated process with
  a hard memory limit, which is future work, not implemented today. This is a
  local resource-exhaustion risk (the app or the conversion has to be restarted),
  not a data-exposure or code-execution one.
- **Third-party ML libraries are trusted the same way any PDF-parsing dependency
  is** — Markwright does not re-implement PDF parsing itself; that trust is no
  different from trusting any other PDF reader. `huggingface_hub`'s optional
  usage telemetry is disabled unconditionally from the very first run; as of this
  writing, `docling`, `easyocr`, `torch` and `pypdf` have no telemetry mechanism
  of their own.

## Dependencies

Dependencies are pinned by hash (`uv.lock`) and reviewed when added or updated.
Automated vulnerability scanning (Dependabot / `pip-audit` in CI) is planned but
not running yet.
