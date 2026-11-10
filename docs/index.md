# texport

Save figures, tables, and in-text numbers from Python for direct use in a LaTeX paper.
Rerun your analysis and recompile: the paper picks up the current results, and JSON
and CSV sidecars keep the underlying values available.

## Install

Requires Python 3.10 or newer. Install from GitHub:

```sh
uv add "texport[all] @ git+https://github.com/josephbb/texport.git@v0.1.0"
# Or:
pip install "texport[all] @ git+https://github.com/josephbb/texport.git@v0.1.0"
```

The number writer has no third-party dependencies. Choose `[figures]` or `[tables]`
instead of `[all]` to install only the corresponding optional dependencies, or omit
extras to export numbers alone.

## Export from Python

```python
import matplotlib.pyplot as plt
import pandas as pd
import texport as tx

tx.save_numbers(
    {"beta_mean": 0.1, "beta_low": -0.2, "beta_high": 0.2},
    "outcomeOne",
)
tx.save_numbers(1234, "nObs")

fig, ax = plt.subplots()
ax.scatter([0, 1, 2], [0.1, 0.8, 1.9])
tx.save_fig("scatter", fig=fig, formats=("pdf", "png"), dpi=300)

summary = pd.DataFrame({"mean": [0.1, 0.9]}, index=["x", "y"])
tx.save_table(summary, "summary", float_format="%.2f")
```

Outputs go to `./artifacts`. Use `tx.configure("path/to/artifacts")` to change the
root. Each save refreshes `artifacts.tex`:

```text
artifacts/
  .texport
  artifacts.tex
  figures/scatter.pdf
  figures/scatter.png
  tables/summary.tex
  tables/summary.csv
  numbers/outcomeOne.tex
  numbers/outcomeOne.json
  numbers/nObs.tex
  numbers/nObs.json
```

## Use in LaTeX

Load the index in the preamble after your own package declarations:

```latex
\documentclass{article}
\usepackage[T1]{fontenc}
\input{artifacts/artifacts.tex}

\begin{document}
We analysed \nObs{} observations. The slope was \outcomeOneBetaMean{}
(95\% CI \outcomeOneBetaLow{} to \outcomeOneBetaHigh{}).

\includegraphics[width=0.6\linewidth]{scatter}
\arttable{summary}
\end{document}
```

The index loads the number commands and required table packages, and appends the
figure directory to the graphics search path. Number digits match the surrounding
text font. Identical output bytes preserve file modification times.

Read the [API guide](api.md) for formatting and cleanup, or the
[LaTeX guide](latex.md) for naming, paths, fonts, and Overleaf.

```{toctree}
:maxdepth: 2
:caption: Documentation

api
latex
reference
development
changelog
```
