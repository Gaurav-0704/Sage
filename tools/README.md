# Dev tools

## `scan.py` — error scanner

Runs static analysis on the whole project and prints a tidy report.

```bash
# from the project root (D:\Projects\NHS App)
python tools/scan.py                  # scan everything
python tools/scan.py --backend        # Python only
python tools/scan.py --frontend       # JS only
python tools/scan.py --explain        # also explain each issue with Claude
```

The scanner auto-installs `ruff` and `pyflakes` if they're missing, and
uses the ESLint that ships with `react-scripts` (no extra install needed).

To enable AI explanations, set an API key first:

```bash
set ANTHROPIC_API_KEY=sk-ant-...
python tools/scan.py --explain
```
