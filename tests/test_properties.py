import re
import string

from hypothesis import given, strategies as st

import texport as tx
from texport.core import _format_value


@given(st.lists(st.one_of(st.text(max_size=40), st.text(alphabet=string.ascii_letters + string.digits + "_- .", max_size=40)), min_size=1, max_size=4))
def test_macro_names_are_ascii_letters_or_rejected(parts):
    try:
        name = tx.macro_name(*parts)
    except ValueError:
        return
    assert re.fullmatch(r"[A-Za-z]+", name)
    assert not name.startswith("end")
    assert name != "relax"
    assert all(part.isascii() for part in parts)


@given(st.floats(allow_nan=False, allow_infinity=False), st.integers(min_value=0, max_value=12))
def test_float_formatting_round_trips(value, digits):
    latex = _format_value(value, None, digits)
    plain = latex.replace(r"\ensuremath{-}", "-").replace("{,}", ",")
    assert float(plain) == float(f"{value:.{digits}f}")
