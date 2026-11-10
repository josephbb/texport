import pytest

import texport as tx
from texport import core


@pytest.fixture(autouse=True)
def root(tmp_path):
    previous = core._ROOT
    path = tx.configure(tmp_path / "artifacts")
    yield path
    core._ROOT = previous


@pytest.fixture
def figure():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    yield fig
    plt.close(fig)
