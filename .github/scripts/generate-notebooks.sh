#!/usr/bin/env bash
set -euo pipefail

for source in "${@:?Pass *_notebook.py source paths}"; do
    jupytext --to notebook --output "${source%_notebook.py}.ipynb" "$source"
done
