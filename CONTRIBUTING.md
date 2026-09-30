# Contributing to songbench

Thanks for helping improve songbench. Bug reports and focused pull requests are
welcome. For changes to scoring rules, explain which examples change and why;
benchmark results can shift even when the CLI still works.

## Local development

Use Python 3.10 or newer. Install the package and test dependencies, then run
the network free public suite:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
```

To inspect a change without an API key, run:

```sh
songbench check examples/two_voices.txt
songbench run --model demo/first --model demo/second --dry-run
```

Add tests for behavior changes, especially parsing, retry decisions, scoring,
and run file compatibility. Keep examples small and synthetic.

## Public content

This repository is public. Do not commit real song lyrics, parody lyrics based
on real songs, API keys, or model transcripts that contain them. Use synthetic
text in public examples and tests. Keep private templates, presets, scenarios,
and tests under their respective `local/` directories, and generated runs under
`runs/`; these paths are ignored. Before opening a pull request, review the
files and diff you are about to publish. Git ignore rules do not erase content
already committed to history.

See [docs/authoring.md](docs/authoring.md) for the template format and
[docs/reference.md](docs/reference.md) for CLI and scoring details.
