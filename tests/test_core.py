import datetime
import json
import os
from decimal import Decimal

import pytest

import texport as tx


def test_macro_name():
    assert tx.macro_name("outcomeOne", "beta_mean") == "outcomeOneBetaMean"
    assert tx.macro_name("model2", "r2") == "modelTwoRTwo"
    assert tx.macro_name("OLS-fit", "p value") == "OLSFitPValue"


@pytest.mark.parametrize("name", ["", "___", "end", "ending", "end-item", "relax", "café", "model٢"])
def test_invalid_macro_name(name):
    with pytest.raises(ValueError):
        tx.macro_name(name)


def test_configure_expands_home_and_resolves(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert tx.configure("~/work/../artifacts") == tmp_path / "artifacts"


def test_save_numbers(root):
    tx.save_numbers({"beta_mean": 0.1, "beta_low": -0.2, "n": 12345, "label": "a_b"}, "outcomeOne")
    tex = (root / "numbers" / "outcomeOne.tex").read_text(encoding="utf-8")
    assert r"\newcommand{\outcomeOneBetaMean}{0.10}" in tex
    assert r"\newcommand{\outcomeOneBetaLow}{\ensuremath{-}0.20}" in tex
    assert r"\newcommand{\outcomeOneN}{12{,}345}" in tex
    assert r"\newcommand{\outcomeOneLabel}{a\_b}" in tex
    raw = json.loads((root / "numbers" / "outcomeOne.json").read_text(encoding="utf-8"))
    assert raw == {"beta_mean": 0.1, "beta_low": -0.2, "n": 12345, "label": "a_b"}
    assert r"\input{\artifactsdir/numbers/outcomeOne}" in (root / "artifacts.tex").read_text()


@pytest.mark.parametrize(
    ("value", "fmt", "expected"),
    [
        (0.000312, ".1e", r"3.1\ensuremath{{}\times 10^{-4}}"),
        (-0.000312, ".1E", r"\ensuremath{-}3.1\ensuremath{{}\times 10^{-4}}"),
        (12345, ",d", "12{,}345"),
        (12345, "_d", r"12\,345"),
        (0.1234, ".1%", r"12.3\%"),
        (float("inf"), None, r"\ensuremath{\infty}"),
        (float("-inf"), None, r"\ensuremath{-}\ensuremath{\infty}"),
    ],
)
def test_number_formats(root, value, fmt, expected):
    path = tx.save_numbers(value, "result", fmt=fmt)
    assert rf"\newcommand{{\result}}{{{expected}}}" in path.read_text()


def test_fmt_mapping_looks_up_scalar_name():
    path = tx.save_numbers(0.125, "estimate", fmt={"estimate": ".3f"})
    assert r"\newcommand{\estimate}{0.125}" in path.read_text()


@pytest.mark.parametrize("values, fmt", [(1, {"wrong": ".1f"}), ({"a": 1}, {"b": ".1f"})])
def test_unknown_fmt_keys_raise(values, fmt):
    with pytest.raises(ValueError):
        tx.save_numbers(values, "estimate", fmt=fmt)


def test_callable_fmt_applies_to_strings_and_numbers():
    path = tx.save_numbers({"label": "a_b", "value": 2}, "formatted", fmt=lambda x: rf"\textbf{{{x}}}")
    tex = path.read_text()
    assert r"\newcommand{\formattedLabel}{\textbf{a_b}}" in tex
    assert r"\newcommand{\formattedValue}{\textbf{2}}" in tex


def test_strings_are_escaped():
    path = tx.save_numbers('\\&%$#_{}~^<>|"', "label")
    expected = (
        r"\textbackslash{}\&\%\$\#\_\{\}\textasciitilde{}"
        r'\textasciicircum{}\textless{}\textgreater{}\textbar{}"'
    )
    assert rf"\newcommand{{\label}}{{{expected}}}" in path.read_text()


def test_numpy_scalars_decimal_and_series(root):
    import numpy as np
    import pandas as pd

    tx.save_numbers(pd.Series({"count": np.int64(1234), "mean": np.float64(0.125)}), "series")
    raw = json.loads((root / "numbers" / "series.json").read_text())
    assert raw == {"count": 1234, "mean": 0.125}
    path = tx.save_numbers({"bool": np.bool_(True), "decimal": Decimal("1.234567890123456789")}, "exact")
    assert r"\newcommand{\exactDecimal}{1.23}" in path.read_text()
    assert json.loads((root / "numbers" / "exact.json").read_text())["decimal"] == "1.234567890123456789"


@pytest.mark.parametrize("value", [float("nan"), Decimal("NaN")])
def test_nan_rejected(value):
    with pytest.raises(ValueError):
        tx.save_numbers(value, "bad")


@pytest.mark.parametrize("value", [None, object(), datetime.date(2025, 1, 1), 1 + 2j, [1, 2]])
def test_unsupported_values_name_macro(value):
    with pytest.raises(TypeError, match="badValue"):
        tx.save_numbers({"value": value}, "bad")


def test_numpy_non_numeric_scalars_and_pandas_na_rejected():
    import numpy as np
    import pandas as pd

    for value in [np.datetime64("2025-01-01"), np.complex128(1j), pd.NA, np.array([1])]:
        with pytest.raises(TypeError, match="badValue"):
            tx.save_numbers({"value": value}, "bad")


def test_macro_collision_within_save():
    with pytest.raises(ValueError, match="both map"):
        tx.save_numbers({"beta_mean": 1, "betaMean": 2}, "x")


def test_series_duplicate_labels_are_rejected():
    import pandas as pd

    with pytest.raises(ValueError, match="both map"):
        tx.save_numbers(pd.Series([1, 2], index=["beta", "beta"]), "fit")


def test_extended_numpy_float_json_preserves_precision(root):
    import numpy as np

    value = np.longdouble("1.234567890123456789")
    tx.save_numbers(value, "precise")
    raw = json.loads((root / "numbers" / "precise.json").read_text())["precise"]
    # Some platforms alias longdouble to float64; others need a string.
    expected = value.item() if isinstance(value.item(), float) else str(value)
    assert raw == expected


def test_macro_collision_between_files_is_rejected_before_writing(root):
    tx.save_numbers({"beta_mean": 1}, "x")
    before = (root / "artifacts.tex").read_bytes()
    with pytest.raises(ValueError, match="xBetaMean"):
        tx.save_numbers(2, "xBetaMean")
    assert not (root / "numbers" / "xBetaMean.tex").exists()
    assert (root / "artifacts.tex").read_bytes() == before
    tx.save_numbers({"beta_mean": 3}, "x")


@pytest.mark.parametrize("name", ["artifactsdir", "arttable", "artfig", "texportloaded"])
def test_reserved_macros(name):
    with pytest.raises(ValueError):
        tx.save_numbers(1, name)


@pytest.mark.parametrize("writer", [lambda name: tx.save_numbers(1, name), lambda name: tx.save_table("table", name)])
def test_case_only_artifact_collision(writer):
    writer("Result")
    with pytest.raises(ValueError):
        writer("result")


@pytest.mark.parametrize("name", ["", "../escape", "with space", "a/b", "café"])
def test_invalid_artifact_names(name):
    with pytest.raises(ValueError):
        tx.save_numbers(1, name)


def test_index_filters_junk_and_keeps_valid_old_number_files(root):
    tx.save_numbers(1, "old")
    (root / "numbers" / "old (conflicted copy).tex").write_text("invalid tex")
    (root / "numbers" / "._old.tex").write_text("invalid tex")
    tx.save_numbers(2, "new")
    index = (root / "artifacts.tex").read_text()
    assert r"\input{\artifactsdir/numbers/old}" in index
    assert r"\input{\artifactsdir/numbers/new}" in index
    assert "conflicted" not in index
    assert "._old" not in index
    assert r"\graphicspath" not in index
    for package in ["graphicx", "booktabs", "multirow"]:
        assert rf"\RequirePackage{{{package}}}" in index


def test_clean_requires_ownership_marker(root):
    root.mkdir()
    sentinel = root / "important.txt"
    sentinel.write_text("keep me")
    tx.save_numbers(1, "value")
    assert not (root / ".texport").exists()
    with pytest.raises((ValueError, RuntimeError)):
        tx.clean()
    assert sentinel.read_text() == "keep me"
    assert (root / "numbers" / "value.tex").exists()


def test_clean_removes_managed_artifacts_and_preserves_other_files(root):
    tx.save_numbers(1, "value")
    tx.save_table("table", "summary")
    (root / "figures").mkdir()
    (root / "figures" / "old.pdf").write_bytes(b"old")
    (root / "notes.txt").write_text("keep me")
    assert (root / ".texport").is_file()
    tx.clean()
    for name in ["numbers", "tables", "figures", "artifacts.tex"]:
        assert not (root / name).exists()
    assert (root / "notes.txt").read_text() == "keep me"
    assert (root / ".texport").is_file()
    tx.clean()
    tx.save_numbers(2, "fresh")
    assert "value}" not in (root / "artifacts.tex").read_text()


def test_unchanged_text_outputs_preserve_mtime(root):
    import pandas as pd

    frame = pd.DataFrame({"a": [1.234]})
    tx.save_numbers({"estimate": 0.12345, "label": "café"}, "fit")
    tx.save_table(frame, "summary")
    paths = [p for p in root.rglob("*") if p.is_file()]
    for path in paths:
        os.utime(path, ns=(1_000_000_000, 1_000_000_000))
    tx.save_numbers({"estimate": 0.12345, "label": "café"}, "fit")
    tx.save_table(frame, "summary")
    assert all(path.stat().st_mtime_ns == 1_000_000_000 for path in paths)
    assert json.loads((root / "numbers" / "fit.json").read_bytes())["label"] == "café"


def test_failed_atomic_write_keeps_previous_outputs(monkeypatch, root):
    tx.save_numbers(1, "result")
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}

    def fail_replace(*args, **kwargs):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replacement failure"):
        tx.save_numbers(2, "result")
    after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert after == before


def test_save_fig(root, figure):
    paths = tx.save_fig("line", fig=figure, formats=("pdf", "png"), dpi=50)
    assert [p.name for p in paths] == ["line.pdf", "line.png"]
    assert all(p.exists() and p.stat().st_size > 0 for p in paths)
    tx.save_fig("line", fig=figure, formats="svg")
    assert sorted(p.name for p in (root / "figures").iterdir()) == ["line.svg"]


def test_save_fig_requires_existing_current_figure(root):
    import matplotlib.pyplot as plt

    plt.close("all")
    with pytest.raises((ValueError, RuntimeError)):
        tx.save_fig("empty")
    assert not plt.get_fignums()


def test_save_fig_format_typo_and_case_collision(figure):
    with pytest.raises(TypeError, match="formats"):
        tx.save_fig("line", fig=figure, format="png")
    tx.save_fig("Line", fig=figure)
    with pytest.raises(ValueError):
        tx.save_fig("line", fig=figure)


def test_unchanged_figure_outputs_preserve_mtime(figure):
    paths = tx.save_fig("line", fig=figure, formats=("pdf", "svg"))
    contents = [path.read_bytes() for path in paths]
    for path in paths:
        os.utime(path, ns=(1_000_000_000, 1_000_000_000))
    tx.save_fig("line", fig=figure, formats=("pdf", "svg"))
    assert [path.read_bytes() for path in paths] == contents
    assert all(path.stat().st_mtime_ns == 1_000_000_000 for path in paths)


def test_invalid_figure_format_preserves_existing_outputs(root, figure):
    tx.save_fig("line", fig=figure, formats=("pdf", "png"))
    before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
    with pytest.raises(ValueError, match="format"):
        tx.save_fig("line", fig=figure, formats=("svg", "notformat"))
    assert {path: path.read_bytes() for path in root.rglob("*") if path.is_file()} == before


def test_save_table(root):
    import pandas as pd

    frame = pd.DataFrame({"label": ["a_b & c"], "value": [1.234]})
    path = tx.save_table(frame, "summary", float_format="%.1f", index=False)
    body = path.read_text()
    assert "1.2" in body and "1.234" not in body
    assert r"a\_b \& c" in body
    assert pd.read_csv(root / "tables" / "summary.csv")["value"].tolist() == [1.234]
    tx.save_table(r"\begin{tabular}{c}raw\end{tabular}", "summary")
    assert not (root / "tables" / "summary.csv").exists()
    assert r"\begin{tabular}{c}raw\end{tabular}" in path.read_text()


def test_save_table_can_disable_escaping():
    import pandas as pd

    path = tx.save_table(pd.DataFrame({"a": [r"$x_1$"]}), "math", escape=False)
    assert "$x_1$" in path.read_text()


def test_raw_table_rejects_dataframe_kwargs():
    with pytest.raises(TypeError):
        tx.save_table("raw", "summary", index=False)
