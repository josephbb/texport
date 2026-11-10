# texport

Save figures, tables, and in-text numbers from Python for direct use in a LaTeX paper. Rerun your analysis and recompile: the paper uses the updated artifacts, while JSON and CSV sidecars keep the underlying values available.

Requires Python 3.10 or newer. The core number writer has no third-party dependencies; figures use matplotlib and tables use pandas and Jinja2.

## Install

Install from GitHub:

```sh
uv add "texport[all] @ git+https://github.com/josephbb/texport.git@v0.1.0"
# Or:
pip install "texport[all] @ git+https://github.com/josephbb/texport.git@v0.1.0"
```

Use `[figures]` or `[tables]` instead of `[all]` to install only the corresponding optional dependencies. Omit extras to export numbers alone.

To develop texport alongside another local project:

```sh
uv add --editable /Users/jbakcoleman/Projects/PyLaTeX
```

Install the optional dependencies in that project too if needed, for example with `uv add matplotlib pandas jinja2`.

## Quickstart

Run this from the directory containing your paper:

```python
import matplotlib.pyplot as plt
import pandas as pd
import texport as tx

tx.save_numbers(
    {"beta_mean": 0.1, "beta_low": -0.2, "beta_high": 0.2},
    "outcomeOne",
)
tx.save_numbers(1234, "nObs")
tx.save_numbers({"p": 0.00031}, "test", fmt={"p": ".1e"})

fig, ax = plt.subplots()
ax.scatter([0, 1, 2], [0.1, 0.8, 1.9])
tx.save_fig("scatter", fig=fig, formats=("pdf", "png"), dpi=300)

summary = pd.DataFrame({"mean": [0.1, 0.9]}, index=["x", "y"])
tx.save_table(summary, "summary", float_format="%.2f")
```

The default output directory is `./artifacts`. Change it with `tx.configure("path/to/artifacts")`. Each save refreshes the index:

```text
artifacts/
  .texport                 # marks a directory created by texport
  artifacts.tex            # loads number macros and artifact helpers
  figures/scatter.pdf
  figures/scatter.png
  tables/summary.tex
  tables/summary.csv        # underlying data
  numbers/outcomeOne.tex
  numbers/outcomeOne.json   # unrounded values
  numbers/nObs.tex
  numbers/nObs.json
  numbers/test.tex
  numbers/test.json
```

In the paper, load the index **after your own package declarations**, in the preamble:

```latex
\documentclass{article}
\usepackage[T1]{fontenc}
\input{artifacts/artifacts.tex}

\begin{document}
We analysed \nObs{} observations. The slope was \outcomeOneBetaMean{}
(95\% CI \outcomeOneBetaLow{} to \outcomeOneBetaHigh{}), with p = \testP{}.

\begin{figure}[ht]
  \centering
  \includegraphics[width=0.6\linewidth]{scatter}
  \caption{Observed values.}
\end{figure}

\arttable{summary}
\end{document}
```

The index loads `graphicx`, `booktabs`, and `multirow`, appends the figure directory to the existing graphics search path, and defines `\arttable{name}` and `\artfig[options]{name}`. It derives `\artifactsdir` from the index's input path when available. You can override it before loading the index:

```latex
\newcommand{\artifactsdir}{results/artifacts}
\input{results/artifacts/artifacts.tex}
```

## Names and formatting

Artifact names accept ASCII letters, digits, `_`, and `-`. Macro names preserve the first word's case, capitalize subsequent words, and spell out digits:

| Python call | LaTeX command |
| --- | --- |
| `tx.macro_name("outcomeOne", "beta_mean")` | `\outcomeOneBetaMean` |
| `tx.macro_name("model2", "r2")` | `\modelTwoRTwo` |
| `tx.macro_name("OLS-fit", "p value")` | `\OLSFitPValue` |

Duplicate generated macros, case-only artifact name collisions, and reserved helper names raise errors before writing. Names beginning with `end`, the name `relax`, and non-ASCII macro names are rejected. Other clashes with commands defined by LaTeX packages are caught by LaTeX's `\newcommand`.

Floats default to two decimal places, integers get thousands separators, and strings are LaTeX-escaped. Number digits stay in text mode so they match the surrounding font; minus signs, exponents, and infinity use small `\ensuremath` fragments. NaN is rejected. JSON sidecars preserve Decimal values and infinities as strings. Pass `digits=3`, `fmt=".3f"`, a dictionary of per-key formats, or a callable returning trusted LaTeX. A scalar's format dictionary uses its artifact name as the key. Callables also receive string values.

## Repeated analyses

Identical output bytes are left untouched, preserving modification times so LaTeX builds can avoid needless work. Saving a figure renders all requested formats before removing obsolete formats of that name. PDF/SVG date metadata is suppressed by default and SVG IDs are stable for each artifact. Replacing a table with raw LaTeX or a Styler removes its old CSV sidecar.

Number files remain in the index until removed. For analyses whose outputs can disappear between runs, start fresh:

```python
import texport as tx

root = tx.configure("artifacts")
if root.exists():
    tx.clean()
# Run the analysis and save its current outputs.
```

`clean()` removes `figures/`, `tables/`, `numbers/`, and `artifacts.tex`, retaining the root and its marker. It raises unless the root contains a `.texport` marker created when texport made the root. An existing directory is never automatically claimed, so choose a new output directory if you want managed cleanup. Files outside those generated paths are preserved.

## Example and development

```sh
uv sync --all-extras
uv run pytest
cd example
uv run python analysis.py
latexmk -pdf paper.tex
```

The example calculates a fitted slope, bootstrap interval, and normal-approximation p-value, then exports its figure, table, and numbers.

Tests include Hypothesis properties and actual LaTeX compilation. Compilation tests skip when `pdflatex` is unavailable; install LaTeX with `graphicx`, `booktabs`, and `multirow` to run them. Use `uv run pytest -m "not latex"` for the Python-only suite. CI runs the full suite on Python 3.10 and 3.14 with LaTeX installed.

Read the [documentation website](https://joebakcoleman.com/texport/),
[API guide](docs/api.md), [LaTeX guide](docs/latex.md), and [changelog](CHANGELOG.md).

Build a searchable documentation website, including the Python reference generated
from docstrings:

```sh
uv run --no-default-groups --group docs sphinx-build -b html -W --keep-going docs docs/_build/html
```

The documentation workflow checks pull requests and automatically publishes
successful builds on `main` to GitHub Pages. See the
[documentation publishing guide](docs/development.md) for details and the local
preview command.

## License

[MIT](LICENSE), copyright 2026 Joseph Bak-coleman.
