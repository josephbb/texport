"""Toy analysis: run from this directory with `uv run python analysis.py`."""

import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import texport as tx

# Remove artifacts left by an earlier run, including numbers no longer saved.
root = tx.configure()
if root.exists():
    tx.clean()

rng = np.random.default_rng(1)
x = rng.normal(size=500)
y = 0.1 * x + rng.normal(scale=0.5, size=500)

(slope, intercept), covariance = np.polyfit(x, y, 1, cov=True)
# Two-sided normal approximation from the fitted slope's standard error.
z = slope / math.sqrt(covariance[0, 0])
p_value = math.erfc(abs(z) / math.sqrt(2))
boot = [np.polyfit(*(lambda i: (x[i], y[i]))(rng.integers(0, 500, 500)), 1)[0] for _ in range(1000)]
low, high = np.percentile(boot, [2.5, 97.5])

# Numbers for the text -> \outcomeOneBetaMean, \outcomeOneBetaLow, ...
tx.save_numbers({"beta_mean": slope, "beta_low": low, "beta_high": high}, "outcomeOne")
tx.save_numbers(len(x), "nObs")
tx.save_numbers({"p": p_value}, "outcomeOne_test", fmt={"p": ".1e"})

plt.figure(figsize=(4, 3))
plt.scatter(x, y, s=5, alpha=0.5)
plt.plot(np.sort(x), intercept + slope * np.sort(x), color="k")
plt.xlabel("x")
plt.ylabel("y")
tx.save_fig("scatter", formats=("pdf", "png"), dpi=300)
plt.close()

summary = pd.DataFrame({"mean": [x.mean(), y.mean()], "sd": [x.std(), y.std()]}, index=["x", "y"])
tx.save_table(summary, "summary", float_format="%.2f", caption="Summary statistics.", label="tab:summary")
