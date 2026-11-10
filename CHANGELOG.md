# Changelog

## Unreleased

- Build searchable guides and a Python reference from docstrings with Sphinx, and publish automatically through GitHub Pages.

## 0.1.0

- Export in-text values as LaTeX commands with unrounded JSON sidecars, figures in multiple formats, and pandas or raw LaTeX tables with CSV sidecars.
- Generate an index that loads number commands and table packages, resolves artifact paths, and preserves existing graphics paths and the `@` catcode.
- Keep number digits in the surrounding text font; render scientific exponents, minus signs, infinity, grouping, and percentages safely. Escape text and reject unsupported scalar types and NaN.
- Validate macro names, duplicate commands, per-key formats, and case-only artifact collisions. Accept pandas Series and supported NumPy numeric scalars.
- Add marker-protected cleanup, render requested figure formats before removing obsolete exports, and remove stale table CSVs when replaced by raw LaTeX or a Styler.
- Write files atomically as UTF-8, preserving unchanged output modification times; omit default PDF/SVG date metadata and stabilize SVG IDs per artifact.
- Add Hypothesis properties, actual LaTeX compilation tests, an executable analysis example, API and LaTeX documentation, and CI for Python 3.10 and 3.14.
