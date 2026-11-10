# API reference

```python
import texport as tx
```

All paths returned by the writers are absolute `pathlib.Path` objects. Text is written as UTF-8, and each output is replaced atomically only when its bytes differ. Every save regenerates `artifacts.tex` from the current number files. Matplotlib and pandas are optional dependencies.

## `configure(root="artifacts") -> Path`

Set the output root for subsequent saves and `clean()`. Expands `~` and resolves relative paths against the current working directory. Returns the resolved path without creating it.

Without an explicit configuration, the default `artifacts` directory is resolved against the working directory at the time of a save.

```python
root = tx.configure("results/artifacts")
```

When the first save creates a root, texport writes a `.texport` marker. Saving into an existing root is allowed but does not add a marker or enable cleanup there.

## `save_numbers(values, name, digits=2, fmt=None) -> Path`

Write `numbers/<name>.tex` and `numbers/<name>.json`; return the `.tex` path. A mapping or any object with `.items()`, including a pandas Series, produces one command per key. A scalar produces one command named from the artifact name alone.

```python
tx.save_numbers({"estimate": 0.12345, "n": 12345}, "model2", digits=3)
# \modelTwoEstimate -> 0.123
# \modelTwoN        -> 12{,}345
tx.save_numbers(0.000312, "pval", fmt={"pval": ".1e"})
```

Accepted values are strings, booleans, integers, real numbers, and `decimal.Decimal`. NumPy boolean, integer, and floating scalars are converted to Python scalars. Unsupported values, including complex numbers, dates, and `pandas.NA`, raise `TypeError` identifying the affected macro. NaN raises `ValueError`; positive and negative infinity are supported.

`digits` controls default fixed-point precision. Integers use comma grouping and booleans use their text representation. `fmt` accepts:

- A Python format specification such as `".3f"`, `",.1f"`, or `".1e"`.
- A callable returning trusted LaTeX. It also applies to strings and bypasses automatic escaping and numeric post-processing.
- A dictionary mapping value keys to specifications or callables. Missing entries use the defaults; unmatched keys raise `ValueError`. For scalars, the key is `name`.

Formatted numeric commas, underscores, percent signs, scientific exponents, and a leading minus are converted to appropriate LaTeX. Other strings are escaped automatically. Number digits remain in text mode.

The JSON sidecar contains unrounded values. Decimal values and NumPy extended floats without a lossless Python float equivalent are stored as strings to preserve their precision. Infinities are stored as the strings `"Infinity"` and `"-Infinity"` so the sidecar remains valid JSON. Other NumPy numeric scalars are converted to Python values. Duplicate Series labels raise an error instead of dropping values.

Names must satisfy the artifact naming rules. Duplicate macros within this call or another indexed number file, reserved helper commands, and case-only artifact collisions raise `ValueError`. Re-saving an existing artifact replaces it.

## `save_fig(name, fig=None, formats=("pdf",), **savefig_kwargs) -> list[Path]`

Save a matplotlib figure in each requested format and return the output paths in order. `formats` accepts one extension or an iterable; leading dots are allowed. Extensions are normalized to lowercase and duplicates are removed while preserving order.

```python
fig, ax = plt.subplots()
ax.plot([0, 1], [0, 1])
paths = tx.save_fig("line", fig=fig, formats=("pdf", "png"), dpi=300)
```

If `fig` is omitted, use matplotlib's current figure. Raise if no figure is open. Passing `format=` raises `TypeError`; use `formats=` instead. Other keywords go to `Figure.savefig`, with `bbox_inches="tight"` as the default.

All requested formats are rendered before changing output files, so a rendering failure preserves previous exports. After rendering succeeds, previous files with the same stem and an extension absent from `formats` are deleted, then the new outputs are written. PDF creation dates and SVG dates are omitted by default, and SVG element IDs use a stable salt derived from the artifact name. These defaults make repeated exports reproducible; other figure properties, external metadata, and matplotlib settings can still affect output bytes.

## `save_table(table, name, **to_latex_kwargs) -> Path`

Write `tables/<name>.tex` and return its path. Accept a pandas DataFrame, Series, Styler, or raw LaTeX string. Objects with `to_csv` also produce `tables/<name>.csv`. DataFrame and Series output defaults to `escape=True`; pass `escape=False` for trusted LaTeX content.

```python
tx.save_table(df, "summary", index=False, float_format="%.2f")
tx.save_table(r"\begin{tabular}{c}A\end{tabular}", "small")
```

Keyword arguments go to `to_latex`. A raw LaTeX string must not have extra keyword arguments. Replacing a table with raw LaTeX or a Styler removes any stale CSV sidecar. Styler escaping follows pandas' Styler configuration; escape untrusted content yourself when using raw LaTeX or Styler output.

## `clean() -> None`

Remove generated `figures/`, `tables/`, `numbers/`, and `artifacts.tex` under the configured root. Keep the root, `.texport`, and unrelated files at the root.

The root must contain a regular `.texport` marker file written when texport created the directory. A missing root, an existing directory without that marker, or a symlink marker raises `ValueError`. This requirement prevents cleanup from recursively deleting data in an arbitrary directory.

```python
root = tx.configure("artifacts")
if root.exists():
    tx.clean()
```

## `macro_name(*parts) -> str`

Build a LaTeX command name without the leading backslash. Preserve the first word's case, capitalize each following word, and spell out ASCII digits. Separators are removed. All output characters are ASCII letters.

```python
tx.macro_name("outcomeOne", "beta_mean")  # "outcomeOneBetaMean"
tx.macro_name("OLS-fit", "p value")      # "OLSFitPValue"
tx.macro_name("model2", "r2")            # "modelTwoRTwo"
```

Raise `ValueError` for non-ASCII input, a name with no words, a resulting name beginning with `end`, or the name `relax`. The number writer also rejects names reserved by the generated index: `artifactsdir`, `arttable`, `artfig`, and the internal loading guard `texportloaded`.
