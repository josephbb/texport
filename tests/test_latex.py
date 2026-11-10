import os
from pathlib import Path
import shutil
import string
import subprocess
import sys
from tempfile import TemporaryDirectory

from hypothesis import given, settings, strategies as st
import pytest

import texport as tx


pytestmark = [pytest.mark.latex, pytest.mark.skipif(shutil.which("pdflatex") is None, reason="pdflatex is not installed")]


def compile_tex(directory, source):
    (directory / "paper.tex").write_text(source, encoding="utf-8")
    result = subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
        cwd=directory, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60,
    )
    assert result.returncode == 0, result.stdout[-12000:]
    assert (directory / "paper.pdf").is_file()
    return result.stdout


@settings(max_examples=8, deadline=None)
@given(
    st.text(alphabet=string.ascii_letters + string.digits + string.punctuation + " ", max_size=80),
    st.floats(min_value=-1e8, max_value=1e8, allow_nan=False, allow_infinity=False),
    st.integers(min_value=0, max_value=6),
)
def test_printable_ascii_and_numbers_compile(label, number, digits):
    with TemporaryDirectory() as work:
        directory = Path(work)
        tx.configure(directory / "artifacts")
        tx.save_numbers({"label": label, "value": number}, "sample", digits=digits)
        compile_tex(directory, r"""\documentclass{article}
\input{artifacts/artifacts.tex}
\begin{document}
\sampleLabel{}: \sampleValue{}.
\end{document}
""")


def test_nested_index_preserves_graphics_paths_and_catcode(tmp_path, figure):
    root = tx.configure(tmp_path / "sub" / "arts")
    tx.save_numbers(-0.2, "estimate")
    tx.save_fig("plot", fig=figure)
    tx.save_table(r"\begin{tabular}{c}value\\\hline\estimate{}\end{tabular}", "summary")
    other = tmp_path / "other"
    other.mkdir()
    shutil.copy2(root / "figures" / "plot.pdf", other / "existing.pdf")
    compile_tex(tmp_path, r"""\documentclass{article}
\usepackage{graphicx}
\graphicspath{{other/}}
\makeatletter
\input{sub/arts/artifacts.tex}
\ifnum\catcode`\@=11\else\errmessage{@ catcode changed}\fi
\makeatother
\input{sub/arts/artifacts.tex}
\ifnum\catcode`\@=12\else\errmessage{@ catcode changed}\fi
\ifnum\pdfstrcmp{\artifactsdir}{sub/arts}=0\else\errmessage{incorrect artifacts path}\fi
\begin{document}
\estimate{}.
\includegraphics[width=1cm]{existing}
\includegraphics[width=1cm]{plot}
\artfig[width=1cm]{plot}
\arttable{summary}
\end{document}
""")


def test_explicit_artifactsdir_and_scientific_formats_compile(tmp_path):
    tx.configure(tmp_path / "sub" / "arts")
    tx.save_numbers({"p": -0.00031, "large": 12345, "percent": 0.125, "infinite": float("inf")}, "stats", fmt={"p": ".1e", "percent": ".1%"})
    compile_tex(tmp_path, r"""\documentclass{article}
\usepackage[T1]{fontenc}
\newcommand{\artifactsdir}{sub/arts}
\input{sub/arts/artifacts.tex}
\ifnum\pdfstrcmp{\artifactsdir}{sub/arts}=0\else\errmessage{custom artifacts path changed}\fi
\begin{document}
\statsP{}, \statsLarge{}, \statsPercent{}, \statsInfinite{}.
\end{document}
""")


def test_index_in_document_directory_uses_dot(tmp_path):
    tx.configure(tmp_path)
    tx.save_numbers(1, "estimate")
    compile_tex(tmp_path, r"""\documentclass{article}
\input{artifacts.tex}
\ifnum\pdfstrcmp{\artifactsdir}{.}=0\else\errmessage{empty artifacts path not normalized}\fi
\begin{document}\estimate{}.\end{document}
""")


def test_missing_currentfilepath_uses_folder_name(tmp_path):
    tx.configure(tmp_path / "arts")
    tx.save_table("raw", "summary")
    compile_tex(tmp_path, r"""\documentclass{article}
\usepackage{graphicx,booktabs,multirow}
\makeatletter
\let\savedpath\CurrentFilePath
\let\CurrentFilePath\undefined
\@@input arts/artifacts.tex
\let\CurrentFilePath\savedpath
\makeatother
\ifnum\pdfstrcmp{\artifactsdir}{arts}=0\else\errmessage{incorrect fallback artifacts path}\fi
\begin{document}Fallback path.\end{document}
""")


def test_example_runs_and_compiles(tmp_path):
    project = Path(__file__).resolve().parents[1]
    for name in ["analysis.py", "paper.tex"]:
        shutil.copy2(project / "example" / name, tmp_path / name)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(project / "src"), env.get("PYTHONPATH")]))
    result = subprocess.run(
        [sys.executable, "analysis.py"], cwd=tmp_path, env=env,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120,
    )
    assert result.returncode == 0, result.stdout
    compile_tex(tmp_path, (tmp_path / "paper.tex").read_text())
