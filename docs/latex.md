# Using artifacts in LaTeX

## Load the generated index

Load `artifacts.tex` in the preamble, after your own `\usepackage` lines:

```latex
\documentclass{article}
\usepackage[T1]{fontenc}
\usepackage{graphicx}
\graphicspath{{other-figures/}}
\input{artifacts/artifacts.tex}

\begin{document}
The estimate was \outcomeOneBetaMean{}.
\end{document}
```

The index loads `graphicx`, `booktabs`, and `multirow`. Declaring packages first lets you choose their options without a later option clash. Existing graphics search paths are preserved and the artifact figure directory is appended. Loading the same generated index twice is harmless; its definitions run only once per document.

## Paths and `\artifactsdir`

The index derives `\artifactsdir` from LaTeX's `\CurrentFilePath` when available, so this works for an index in a nested folder:

```latex
\input{results/artifacts/artifacts.tex}
```

Older engines without that path information fall back to the configured root's folder name. An empty path becomes `.`. If the fallback does not match the paper's directory structure, define `\artifactsdir` yourself before loading the index; your definition takes precedence:

```latex
\newcommand{\artifactsdir}{../analysis/artifacts}
\input{../analysis/artifacts/artifacts.tex}
```

Use paths relative to the main document's working directory. Keep artifact root paths simple and avoid TeX-special characters in folder names.

## Macro names

Artifact filenames accept only ASCII letters, digits, `_`, and `-`. Generated number commands use ASCII letters only, preserving the first word's case, capitalizing later words, and spelling out digits.

| Export | Command |
| --- | --- |
| `tx.save_numbers(1234, "nObs")` | `\nObs` |
| `tx.save_numbers({"beta_mean": 0.1}, "outcomeOne")` | `\outcomeOneBetaMean` |
| `tx.save_numbers({"r2": 0.9}, "model2")` | `\modelTwoRTwo` |
| `tx.save_numbers({"p": 0.01}, "OLS-fit")` | `\OLSFitP` |

Use `tx.macro_name(...)` to inspect a generated name. Add `{}` after commands in prose to preserve the following space: `\nObs{} observations`.

Names beginning with `end` and the command `relax` are invalid for `\newcommand`. The helper names `artifactsdir`, `arttable`, and `artfig`, and the internal loading guard `texportloaded`, are reserved. Texport rejects duplicate macros across saved number files and filenames differing only by case within the same artifact subdirectory. Other collisions with document or package commands cause a LaTeX error, because generated values use `\newcommand`.

## Formatting and fonts

Default floats use two decimal places, integers get thousands separators, and strings are escaped. Digits remain in text mode so values match the surrounding prose font. A leading minus, a scientific exponent, or infinity uses an `\ensuremath` fragment:

| Value and format | Generated value |
| --- | --- |
| `-0.2` | `\ensuremath{-}0.20` |
| `12345` | `12{,}345` |
| `0.000312`, `fmt=".1e"` | `3.1\ensuremath{{}\times 10^{-4}}` |
| `0.12`, `fmt=".0%"` | `12\%` |
| `float("inf")` | `\ensuremath{\infty}` |

Use the commands directly in prose. They also work inside math expressions, where the surrounding math mode determines the digit font:

```latex
The p-value was \testP{}.
\[p = \testP\]
```

String escaping covers backslashes, braces, `_`, `&`, `%`, `$`, `#`, `~`, `^`, `<`, `>`, and `|`. Double quotes are left as literal characters because `\textquotedbl` is unavailable in OT1. Use `\usepackage[T1]{fontenc}` with pdfLaTeX for suitable text glyphs, including straight double quotes. For arbitrary Unicode text, select an engine and fonts that support those characters.

A callable formatter returns trusted LaTeX and bypasses automatic escaping. For example:

```python
tx.save_numbers({"label": "Main result"}, "model", fmt=lambda s: rf"\textbf{{{s}}}")
```

Escape dynamic text yourself inside such a callable if it may contain LaTeX-special characters.

## Figures

```python
tx.save_fig("scatter", fig=fig, formats=("pdf", "png"), dpi=300)
```

Either use the normal graphics command, which searches the artifact figure directory, or the helper, which supplies its path explicitly:

```latex
\includegraphics[width=0.7\linewidth]{scatter}
\artfig[width=0.7\linewidth]{scatter}
```

Use PDF for vector plots with pdfLaTeX; PNG is useful for raster figures. SVG output is available for other uses, but pdfLaTeX does not include SVG directly. Saving the same name with different `formats` removes the old formats that were omitted from the new save. Every requested format is rendered successfully before old files are removed. PDF/SVG date metadata is suppressed by default, and SVG IDs use a stable salt based on the artifact name, helping repeated exports keep identical bytes.

## Tables

```python
tx.save_table(df, "summary", float_format="%.2f", caption="Summary.", label="tab:summary")
```

```latex
\arttable{summary}
```

The helper inputs the saved LaTeX. If the exported table already includes a floating `table` environment through its caption or pandas options, do not wrap it in another one. For a bare `tabular`, add the desired environment in the paper. DataFrame and Series text is escaped by default. Use `escape=False` or raw LaTeX only for trusted content.

## Keeping outputs current

The index discovers all `numbers/*.tex` files with valid artifact stems. Files named like conflicted copies or macOS `._` sidecars are skipped. A valid old number file remains loaded until removed: call `tx.clean()` at the start of an analysis when its output set can change, then save all current artifacts. Cleanup requires a root that texport created and marked with `.texport`.

Unchanged artifact bytes retain their modification times, so repeated saves do not by themselves trigger a rebuild. Cleanup intentionally deletes those artifacts; a run that calls `clean()` recreates them.

## Overleaf

Run the Python analysis locally, then upload or sync the generated `artifacts/` directory to the Overleaf project alongside your main `.tex` file. Keep `artifacts.tex`, `numbers/`, `tables/`, and the figure formats used by the paper together. Overleaf compiles the saved files; it does not run the analysis automatically. Rerun Python and update the uploaded artifacts when the data or analysis changes.

If the uploaded folder has a different path, set `\artifactsdir` explicitly before the index input. Use Overleaf's pdfLaTeX compiler for the included example and ensure all three required LaTeX packages are available.
