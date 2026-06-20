# Notes for LLM contributors

A short orientation file for an LLM working in this repo. Skim before making
changes and keep edits consistent with what's described here. Read
[README.md](README.md) for the user-facing intro.

## What this project is

`pySwitchbot` is a pure-Python library for controlling SwitchBot IoT devices
over **Bluetooth LE** (with some SwitchBot cloud HTTP calls). It backs the
SwitchBot integration in [Home Assistant](https://www.home-assistant.io/).

Built on [`bleak`](https://github.com/hbldh/bleak) +
[`bleak-retry-connector`](https://github.com/Bluetooth-Devices/bleak-retry-connector)
for the BLE transport, `aiohttp` for the cloud API, and
`cryptography`/`pyOpenSSL` for encrypted devices (locks, etc.). It ships its
own advertisement parsing — it does not depend on the `bluetooth-devices`
adv-parser stack.

## Disclosing autonomous contributions

This repo receives a high volume of autonomous, agent-generated pull requests.
When an account is AI-driven, maintainers can only review and have a real
technical discussion if they know **who is responsible** for it.

- If a PR is produced by an autonomous agent, **name the human or team
  responsible** in the PR description (and ideally on the account profile).
- Undisclosed drive-by PRs with no human owner are routinely closed — a single
  line of attribution is what makes the change reviewable.

## Code style

- **Docstrings: terse, default to single-line.** A docstring is the function's
  contract, not a narrative. Almost every docstring should be one line —
  `"""Summary."""`. Multi-line is the exception, only when there's non-obvious
  caller-visible behaviour the signature and parameter names don't convey.
  Note `D1xx` (missing-docstring) rules are ignored — don't add docstrings
  just to satisfy a linter; add them when they carry contract.

- **Comments: same bar — default to none.** Add one only when the _why_ is
  non-obvious: a hidden constraint, a subtle invariant, a workaround for a
  specific device quirk or bug. If removing the comment wouldn't confuse a
  future reader, don't write it. **Don't remove existing comments** unless the
  code they describe is gone.

- **Keep it out of docstrings/comments:** rationale/motivation, issue numbers
  ("closes #N"), and prose that just restates the code. Those belong in the PR
  body and commit message — git already remembers.

- **Python 3.11+.** `python_requires=">=3.11"`, ruff `target-version = "py311"`,
  pyupgrade `--py311-plus`. Don't introduce 3.12+-only syntax.

- **Line length 88**, ruff-enforced (`E501` itself is ignored, but ruff-format
  reflows to 88). Imports sorted by ruff/isort,
  `known-first-party = ["pySwitchbot", "tests"]`.

## Where things live

| Path                      | What                                                                                                                                      |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `switchbot/__init__.py`   | Public API surface — re-exports device classes, enums, `GetSwitchbotDevices`, `parse_advertisement_data`                                  |
| `switchbot/adv_parser.py` | Central BLE advertisement dispatcher — maps service/model bytes to a device type + parser. Touch this to detect a new device              |
| `switchbot/adv_parsers/`  | One pure-function parser per device family (`bot.py`, `curtain.py`, `lock.py`, `meter.py`, `hub2.py`, …)                                  |
| `switchbot/devices/`      | One module per device class (what callers instantiate); `device.py` holds the `SwitchbotDevice` / `SwitchbotEncryptedDevice` base classes |
| `switchbot/const/`        | Enums and constants by domain; `SwitchbotModel` and the exception classes                                                                 |
| `switchbot/models.py`     | `SwitchBotAdvertisement` dataclass                                                                                                        |
| `switchbot/discovery.py`  | `GetSwitchbotDevices` — BLE scan + per-type getters                                                                                       |
| `tests/`                  | Pytest suite                                                                                                                              |

Adding a device usually touches: a parser in `adv_parsers/`, a dispatch entry
in `adv_parser.py`, a class in `devices/`, model/const in `const/`, and an
export in `__init__.py`.

## Running tests

No Poetry/uv — plain pip + setuptools.

```bash
pip install -r requirements_dev.txt .
pytest --cov=switchbot tests
```

CI (`.github/workflows/ci.yaml`) runs the suite on Python 3.11–3.14 plus the
pre-commit hooks, and uploads coverage to Codecov.

## Commit / PR conventions

- **Conventional Commits**, enforced by the `commitizen` commit-msg pre-commit
  hook (default ruleset). Types: `build`, `chore`, `ci`, `docs`, `feat`,
  `fix`, `perf`, `refactor`, `revert`, `style`, `test`. Examples:
  - `feat: add support for the SwitchBot Hub 3`
  - `fix(lock): handle empty advertisement payload`
- **Use a feature branch.** PRs opened from a fork's default branch are
  auto-closed by `auto-close-default-branch-prs.yml`.
- **Pre-commit auto-fixes; re-stage.** `ruff --fix`, `ruff-format`,
  `pyupgrade`, `codespell`, prettier, and the standard pre-commit-hooks run on
  commit and rewrite files in place; when a hook edits a file the commit
  aborts — re-stage and commit again. (pre-commit.ci also autofixes on PRs.)
- **No PR template / no CONTRIBUTING.md** — the body is freeform; describe what
  the change does and why, and link the issue if one exists.
- **Releases are manual:** cutting a GitHub Release triggers
  `python-publish.yml` to build and publish to PyPI. There is no
  semantic-release; nothing auto-bumps from commit types.

## Reporting security issues

Report suspected vulnerabilities privately to the maintainers — not in a public
issue, PR, or commit that names the bug class and affected code path.
