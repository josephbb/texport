# Development and publishing

## Run the package checks

```sh
uv sync --all-extras
uv run pytest
```

Tests include Hypothesis properties and real LaTeX compilation. Install pdfLaTeX
with `graphicx`, `booktabs`, and `multirow` to run the compilation tests; they skip
when `pdflatex` is unavailable. The test workflow covers Python 3.10 and 3.14.

## Build the documentation

Sphinx reads the Markdown guides with MyST and generates the
[Python reference](reference.rst) from the package docstrings with autodoc and
Napoleon. Furo provides navigation, search, and light and dark themes.

```sh
uv run --no-default-groups --group docs sphinx-build -b html -W --keep-going docs docs/_build/html
```

Preview the generated site locally:

```sh
uv run --no-default-groups --group docs python -m http.server --directory docs/_build/html
```

Open `http://localhost:8000`. Generated HTML stays outside version control.

## Automatic GitHub Pages publishing

The documentation workflow builds relevant pushes to `main`, checks pull requests,
and supports manual runs from the Actions tab. It treats Sphinx warnings as errors.
Successful builds on `main` deploy to GitHub Pages; pull requests only build.

The site is served at [joebakcoleman.com/texport](https://joebakcoleman.com/texport/).
Documentation and public API changes publish automatically. The publishing source
is configured under **Settings → Pages → Build and deployment → Source → GitHub
Actions**.

For configuring a fork, see
[GitHub's Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).
