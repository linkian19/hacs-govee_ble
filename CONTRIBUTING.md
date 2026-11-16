# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. If you've changed something, update the documentation.
3. Make sure your code lints (`ruff check .`).
4. Test your contribution (`pytest -q`).
5. Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People _love_ thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

Lint rules are pinned in `ruff.toml`; run [ruff](https://docs.astral.sh/ruff/) before opening a pull request.

## Test your code modification

Every push runs the Validate workflow: ruff, hassfest, HACS validation and `pytest`. To run the checks locally (Python 3.14, Linux or WSL — Home Assistant doesn't run on Windows):

```bash
pip install -r requirements_test.txt ruff==0.17.3
ruff check .
pytest -q
```

`requirements_test.txt` pins one Home Assistant release plus the requirements of HA's `bluetooth` integration, which the tests import. When bumping `pytest-homeassistant-custom-component`, copy the matching pins from `homeassistant/components/{bluetooth,usb}/manifest.json`.

## Releasing

Versions are CalVer (`YYYY.M.patch`) with no `v` prefix.

1. Bump `version` in `custom_components/govee_ble_hacs/manifest.json` and add a `CHANGELOG.md` entry; merge to `main`.
2. Tag the merge commit with the same version and push the tag: `git tag -a 2026.12.0 -m 2026.12.0 && git push origin 2026.12.0`.
3. The Release workflow checks the tag matches `manifest.json`, runs the full Validate workflow on the tagged commit, then publishes the GitHub release with a generated Full Changelog link.
4. Replace the generated body with a short Fixes / Notes summary (kept above the Full Changelog link): `gh release edit <tag> --notes-file notes.md`.

This repo is a fork, so `gh` defaults to the upstream repository. Run `gh repo set-default linkian19/hacs-govee_ble` once in a fresh clone, or pass `-R linkian19/hacs-govee_ble`.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
