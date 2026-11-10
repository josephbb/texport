"""Write analysis artifacts and a relocatable LaTeX index."""

from __future__ import annotations

from contextlib import nullcontext
from decimal import Decimal
from io import BytesIO
import json
import math
from numbers import Integral, Real
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Callable, Iterable, Mapping, Union

DEFAULT_ROOT = "artifacts"
_ROOT: Path | None = None
_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
_COMMAND_PATTERN = re.compile(r"\\newcommand\s*\{\\([A-Za-z]+)\}")
_RESERVED_MACROS = {"artifactsdir", "arttable", "artfig", "texportloaded"}
_DIGIT_WORDS = dict(zip("0123456789", (
    "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
)))
_TEX_SPECIALS = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}", "<": r"\textless{}", ">": r"\textgreater{}",
    "|": r"\textbar{}",
}
Formatter = Union[str, Callable[[Any], str]]


def configure(root: str | Path = DEFAULT_ROOT) -> Path:
    """Set the artifacts directory without creating it.

    Parameters
    ----------
    root : str or pathlib.Path, optional
        Expand ``~`` and resolve relative paths against the working directory.

    Returns
    -------
    pathlib.Path
        The absolute artifacts directory.
    """
    global _ROOT
    _ROOT = Path(root).expanduser().resolve()
    return _ROOT


def _root() -> Path:
    return _ROOT if _ROOT is not None else Path(DEFAULT_ROOT).resolve()


def _atomic_write(path: Path, content: bytes) -> None:
    """Replace a file atomically, preserving its timestamp when unchanged."""
    if path.is_file() and path.read_bytes() == content:
        return
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _ensure_root() -> Path:
    root = _root()
    try:
        root.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        if not root.is_dir():
            raise NotADirectoryError(root)
    else:
        _atomic_write(root / ".texport", b"Created by texport. Allows tx.clean() to remove generated artifacts.\n")
    return root


def _subdir(name: str) -> Path:
    path = _ensure_root() / name
    path.mkdir(exist_ok=True)
    return path


def clean() -> None:
    """Delete generated artifacts from a directory created by texport.

    Remove ``figures/``, ``tables/``, ``numbers/``, and ``artifacts.tex``.
    Keep the root, its ``.texport`` marker, and unrelated files.

    Raises
    ------
    ValueError
        If the configured root has no regular ``.texport`` marker file.
        Pre-existing directories are never marked automatically.
    """
    root = _root()
    marker = root / ".texport"
    if not marker.is_file() or marker.is_symlink():
        raise ValueError(f"refusing to clean {root}: missing .texport marker created by texport")
    for name in ("figures", "tables", "numbers"):
        path = root / name
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.exists():
            shutil.rmtree(path)
    (root / "artifacts.tex").unlink(missing_ok=True)


def _check_name(name: str) -> None:
    if not isinstance(name, str) or not _NAME_PATTERN.fullmatch(name):
        raise ValueError(f"artifact name {name!r} may only contain ASCII letters, digits, '_' and '-'")


def _check_case_collision(subdir: str, name: str) -> None:
    directory = _root() / subdir
    if directory.is_dir():
        for path in directory.iterdir():
            if path.stem != name and path.stem.casefold() == name.casefold():
                raise ValueError(f"artifact names {name!r} and {path.stem!r} differ only in case in {subdir}/")


def macro_name(*parts: str) -> str:
    """Build a LaTeX command name using ASCII letters only.

    Parameters
    ----------
    *parts : str
        Preserve the first word's case, capitalize later words, remove
        separators, and spell out digits.

    Returns
    -------
    str
        Command name without a backslash: ``outcomeOneBetaMean`` for
        ``("outcomeOne", "beta_mean")`` or ``OLSFit`` for ``("OLS-fit",)``.

    Raises
    ------
    ValueError
        If a component is non-ASCII, the result is empty, starts with
        ``end``, or equals ``relax`` (names forbidden by LaTeX).
    """
    words = []
    for part in parts:
        part = str(part)
        if not part.isascii():
            raise ValueError(f"macro name components must be ASCII: {part!r}")
        part = re.sub(r"[0-9]", lambda match: "_" + _DIGIT_WORDS[match.group()] + "_", part)
        words.extend(word for word in re.split(r"[^A-Za-z]+", part) if word)
    if not words:
        raise ValueError(f"cannot build a macro name from {parts!r}")
    name = words[0] + "".join(word[0].upper() + word[1:] for word in words[1:])
    if name.startswith("end") or name == "relax":
        raise ValueError(f"macro name {name!r} is forbidden by LaTeX")
    return name


def _escape(text: str) -> str:
    return "".join(_TEX_SPECIALS.get(character, character) for character in text)


def _normalize_value(value: Any) -> str | Real | Decimal:
    dtype = getattr(value, "dtype", None)
    if getattr(dtype, "kind", None) in ("b", "i", "u", "f") and getattr(value, "ndim", 0) == 0:
        value = value.item()
        # Extended NumPy floats have no lossless Python float equivalent:
        # their item() remains a NumPy scalar. Preserve its precision.
        if getattr(getattr(value, "dtype", None), "kind", None) == "f":
            value = Decimal(str(value))
    if not isinstance(value, (str, Real, Decimal)):
        raise TypeError(f"unsupported value type {type(value).__name__}; expected a real number, Decimal, or str")
    if isinstance(value, Decimal):
        is_nan = value.is_nan()
    elif isinstance(value, Real) and not isinstance(value, Integral):
        is_nan = value != value
    else:
        is_nan = False
    if is_nan:
        raise ValueError("NaN cannot be exported to LaTeX")
    return value


def _format_value(value: Any, fmt: Formatter | None, digits: int) -> str:
    value = _normalize_value(value)
    if callable(fmt):
        result = fmt(value)
        if not isinstance(result, str):
            raise TypeError("a callable formatter must return a string of LaTeX")
        return result
    if isinstance(value, str):
        return _escape(value)
    is_infinite = value.is_infinite() if isinstance(value, Decimal) else (
        value == math.inf or value == -math.inf
    )
    if is_infinite:
        return (r"\ensuremath{-}" if value < 0 else "") + r"\ensuremath{\infty}"
    if not isinstance(value, (int, float, Decimal)):
        value = float(value)
    if fmt is not None:
        text = format(value, fmt)
    elif isinstance(value, bool):
        text = str(value)
    elif isinstance(value, int):
        text = format(value, ",")
    else:
        text = format(value, f".{digits}f")
    text = text.replace(",", "{,}").replace("_", r"\,").replace("%", r"\%")
    text = re.sub(
        r"[eE]([+-]?[0-9]+)$",
        lambda match: rf"\ensuremath{{{{}}\times 10^{{{int(match.group(1))}}}}}",
        text,
    )
    if text.startswith("-"):
        text = r"\ensuremath{-}" + text[1:]
    return text


def _to_jsonable(value: str | Real | Decimal) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, str) or isinstance(value, bool):
        return value
    if isinstance(value, Integral):
        return int(value)
    value = float(value)
    return value if math.isfinite(value) else ("-Infinity" if value < 0 else "Infinity")


def _number_files() -> list[Path]:
    return sorted(path for path in (_root() / "numbers").glob("*.tex") if _NAME_PATTERN.fullmatch(path.stem))


def save_numbers(
    values: Mapping[str, Any] | Any,
    name: str,
    digits: int = 2,
    fmt: Formatter | Mapping[str, Formatter] | None = None,
) -> Path:
    r"""Save values as LaTeX commands and unrounded JSON.

    Parameters
    ----------
    values : mapping, pandas.Series, or scalar
        Real numbers, Decimal values, or strings. Objects with ``items()``
        are treated as mappings; numeric NumPy scalars are supported.
    name : str
        Artifact name. A scalar defines ``\name``; mapping keys are appended
        using :func:`macro_name`.
    digits : int, optional
        Decimal places for floating point numbers; default is 2.
    fmt : str, callable, mapping, or None, optional
        Python format specification, callable returning trusted LaTeX, or
        per-key formatters. A scalar's mapping key is ``name``. Missing
        formatters use the defaults; unknown keys raise ValueError.
        Callables also apply to strings.

    Returns
    -------
    pathlib.Path
        The generated ``numbers/<name>.tex`` file.

    Raises
    ------
    ValueError
        For invalid names, colliding commands, unknown format keys, or NaN.
    TypeError
        For unsupported values, with the affected macro named in the error.

    Notes
    -----
    Decimal values, extended NumPy floats, and infinities are JSON strings
    to preserve precision and valid JSON. Other numbers retain their
    unrounded numeric values.
    Strings are escaped; callable output is inserted verbatim.
    """
    _check_name(name)
    _check_case_collision("numbers", name)
    is_mapping = callable(getattr(values, "items", None))
    items = list(values.items()) if is_mapping else [(name, values)]
    if isinstance(fmt, Mapping):
        unknown = set(fmt) - {key for key, _ in items}
        if unknown:
            raise ValueError(f"fmt keys do not match any value: {sorted(unknown, key=str)!r}")
    lines = [f"% Generated by texport from save_numbers(..., {name!r}). Do not edit."]
    seen: dict[str, Any] = {}
    raw = {}
    for key, value in items:
        macro = macro_name(name, str(key)) if is_mapping else macro_name(name)
        if macro in _RESERVED_MACROS:
            raise ValueError(f"macro \\{macro} is reserved by texport")
        if macro in seen:
            raise ValueError(f"keys {seen[macro]!r} and {key!r} both map to \\{macro}")
        seen[macro] = key
        key_fmt = fmt.get(key) if isinstance(fmt, Mapping) else fmt
        try:
            normalized = _normalize_value(value)
            formatted = _format_value(normalized, key_fmt, digits)
        except (TypeError, ValueError) as error:
            raise type(error)(f"\\{macro}: {error}") from error
        lines.append(rf"\newcommand{{\{macro}}}{{{formatted}}}")
        raw[str(key)] = _to_jsonable(normalized)
    tex_path = _root() / "numbers" / f"{name}.tex"
    for other in _number_files():
        if other == tex_path:
            continue
        duplicates = set(_COMMAND_PATTERN.findall(other.read_text(encoding="utf-8"))) & seen.keys()
        if duplicates:
            macro = sorted(duplicates)[0]
            raise ValueError(f"macro \\{macro} already defined in {other.name}")
    tex_content = ("\n".join(lines) + "\n").encode("utf-8")
    json_content = (json.dumps(raw, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    _subdir("numbers")
    _atomic_write(tex_path, tex_content)
    _atomic_write(tex_path.with_suffix(".json"), json_content)
    _write_index()
    return tex_path


def save_fig(
    name: str,
    fig: Any = None,
    formats: str | Iterable[str] = ("pdf",),
    **savefig_kwargs: Any,
) -> list[Path]:
    """Save a matplotlib figure and remove obsolete formats of that name.

    Parameters
    ----------
    name : str
        Artifact name without an extension.
    fig : matplotlib.figure.Figure or None, optional
        Figure to export. None uses the current figure, if one exists.
    formats : str or iterable of str, optional
        Formats accepted by matplotlib; default is ``("pdf",)``.
    **savefig_kwargs
        Forwarded to ``savefig``. Default ``bbox_inches`` is ``"tight"``.
        Use ``formats=`` rather than ``format=``.

    Returns
    -------
    list of pathlib.Path
        Written figure paths, in format order.

    Raises
    ------
    ValueError
        For invalid names or formats, or when no current figure exists.
    TypeError
        If ``format=`` is supplied.

    Notes
    -----
    PDF/SVG creation timestamps are suppressed by default. SVG IDs use a
    stable salt. Identical bytes leave existing file timestamps unchanged.
    """
    _check_name(name)
    _check_case_collision("figures", name)
    if "format" in savefig_kwargs:
        raise TypeError("use formats= rather than format= with save_fig")
    extensions = [formats] if isinstance(formats, str) else list(formats)
    if not extensions or any(not isinstance(ext, str) or not re.fullmatch(r"\.?[A-Za-z0-9]+", ext) for ext in extensions):
        raise ValueError("formats must contain one or more file extensions")
    extensions = list(dict.fromkeys(ext.lstrip(".").lower() for ext in extensions))
    if fig is None:
        import matplotlib.pyplot as plt

        if not plt.get_fignums():
            raise ValueError("no current matplotlib figure exists; create or pass a figure first")
        fig = plt.gcf()
    savefig_kwargs.setdefault("bbox_inches", "tight")
    rendered = []
    for ext in extensions:
        kwargs = dict(savefig_kwargs)
        if ext in ("pdf", "svg"):
            metadata = dict(kwargs.get("metadata") or {})
            metadata.setdefault("CreationDate" if ext == "pdf" else "Date", None)
            kwargs["metadata"] = metadata
        if ext == "svg":
            import matplotlib

            context = matplotlib.rc_context({"svg.hashsalt": f"texport-{name}"})
        else:
            context = nullcontext()
        with context, BytesIO() as buffer:
            fig.savefig(buffer, format=ext, **kwargs)
            rendered.append(buffer.getvalue())
    out_dir = _subdir("figures")
    paths = [out_dir / f"{name}.{ext}" for ext in extensions]
    for old in out_dir.iterdir():
        if old.is_file() and old.stem == name and old not in paths:
            old.unlink()
    for path, content in zip(paths, rendered):
        _atomic_write(path, content)
    _write_index()
    return paths


def save_table(table: Any, name: str, **to_latex_kwargs: Any) -> Path:
    """Save a pandas table or raw LaTeX, with a CSV for DataFrames/Series.

    Parameters
    ----------
    table : pandas.DataFrame, pandas.Series, pandas.io.formats.style.Styler, or str
        Object exposing ``to_latex()``, or trusted raw LaTeX.
    name : str
        Artifact name without an extension.
    **to_latex_kwargs
        Forwarded to ``to_latex``. Objects with ``to_csv`` default to
        ``escape=True``. Raw strings accept no additional arguments.

    Returns
    -------
    pathlib.Path
        The generated ``tables/<name>.tex`` file. A raw string or Styler
        replaces and removes a previous CSV of the same name.
    """
    _check_name(name)
    _check_case_collision("tables", name)
    csv = None
    if isinstance(table, str):
        if to_latex_kwargs:
            raise TypeError("to_latex keyword arguments only apply to table objects")
        body = table
    else:
        if callable(getattr(table, "to_csv", None)):
            to_latex_kwargs.setdefault("escape", True)
            csv = table.to_csv().encode("utf-8")
        body = table.to_latex(**to_latex_kwargs)
    content = (f"% Generated by texport from save_table(..., {name!r}). Do not edit.\n{body}").encode("utf-8")
    out_dir = _subdir("tables")
    tex_path = out_dir / f"{name}.tex"
    _atomic_write(tex_path, content)
    if csv is None:
        tex_path.with_suffix(".csv").unlink(missing_ok=True)
    else:
        _atomic_write(tex_path.with_suffix(".csv"), csv)
    _write_index()
    return tex_path


def _write_index() -> None:
    root = _ensure_root()
    lines = [
        "% Generated by texport. Do not edit.",
        "% Load in the preamble after your own package declarations.",
        r"\ifdefined\texportloaded\endinput\fi",
        r"\let\texportloaded\relax",
        r"\expandafter\edef\csname texport@restorecatcode\endcsname{\catcode64=\the\catcode64\relax}",
        r"\catcode64=11\relax",
        r"\ifdefined\artifactsdir\else",
        r"  \ifdefined\CurrentFilePath",
        r"    \edef\artifactsdir{\CurrentFilePath}",
        r"  \else",
        rf"    \def\artifactsdir{{{root.name or '.'}}}",
        r"  \fi",
        r"  \ifx\artifactsdir\@empty\def\artifactsdir{.}\fi",
        r"\fi",
        r"\RequirePackage{graphicx}",
        r"\RequirePackage{booktabs}",
        r"\RequirePackage{multirow}",
        r"\ifx\Ginput@path\@undefined\def\Ginput@path{}\fi",
        r"\edef\Ginput@path{\unexpanded\expandafter{\Ginput@path}{\artifactsdir/figures/}}",
        r"\newcommand{\arttable}[1]{\input{\artifactsdir/tables/#1}}",
        r"\newcommand{\artfig}[2][]{\includegraphics[#1]{\artifactsdir/figures/#2}}",
    ]
    lines += [rf"\input{{\artifactsdir/numbers/{path.stem}}}" for path in _number_files()]
    lines += [r"\texport@restorecatcode"]
    _atomic_write(root / "artifacts.tex", ("\n".join(lines) + "\n").encode("utf-8"))
