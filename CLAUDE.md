# ASCII-art

Converts images (.png/.jpg/.jpeg/.webp) to ASCII-art text via a tkinter/customtkinter GUI.

## Commands

```bash
uv sync                                              # install deps
uv run ascii-art                                     # run the GUI
uv run pytest --cov=ascii_art --cov-report=term-missing --cov-branch --cov-fail-under=100   # tests + coverage (matches CI's enforcement)
uv run ruff check .                                  # lint
```

CI (`.github/workflows/ci.yml`) runs lint + tests with coverage on push/PR to `main`.

## Architecture

```text
src/ascii_art/
  main.py            entry point (ascii-art script -> main.main -> user_interface.run)
  user_interface.py   tkinter/customtkinter GUI; module-level globals for window state
  ui_logic.py         pure, tkinter-free helpers (URL validation, download, size parsing) - unit testable
  ascii_generator.py  image -> text conversion; precomputed byte-translation LUT for speed
  paths.py            OS-agnostic filesystem path helpers shared by the two modules above
  display.py          monitor/window-geometry helpers (Win32 work-area lookup, fit/clamp/center math) used by user_interface.py
  translations.py     ENGLISH / CZECH string dicts
tests/                pytest suite, one test file per src module (incl. test_display.py), plus shared _http.py/_paths.py/_tempcwd.py helpers
assets/               sample images used by integration tests
```

## Gotchas

- **Don't run `ruff format`** on `user_interface.py`. Its widget constructors are deliberately kept on one line each (see the `E501` per-file-ignore in `pyproject.toml`) — splitting them across many lines hurts readability more than the long lines do. This is intentional style, not lint debt.
- **100% line coverage is the baseline**, ~99% branch coverage. The one accepted gap is `user_interface.py`'s `menu()` function — its final `elif` has an unreachable "no condition matched" fallthrough that only real UI code paths can never hit; don't write an artificial test to cover it.
- `ui_logic.py` intentionally has zero tkinter/customtkinter imports so it stays unit-testable without a display; new validation/business logic belongs there, not in `user_interface.py`.
- Test helpers (`tests/_http.py::make_response`, `tests/_tempcwd.py::IsolatedTempCwdMixin`) are shared across multiple test files — extend them instead of adding local duplicates.
- GUI tests in `test_user_interface.py` drive the real customtkinter widget tree (not mocked out); nested callbacks aren't exposed as module attributes, so tests find them via each widget's `_command` attribute (see `find_button()`).
- `paths.open_with_default_app` dispatches on `platform.system()` (Windows/macOS/Linux); `os.startfile` only exists as an attribute on Windows, so its test patches it with `create=True` (see `test_paths.py::test_windows_uses_startfile`) — needed on any OS other than Windows, or the patch itself would fail.
- When running `/simplify` iteratively, check `git diff HEAD~1...HEAD --stat` first: once a fix shrinks to a few lines, skip re-spawning the 4-agent review and just re-verify directly (ruff + pytest) — a fresh pass on a trivial diff won't surface anything new.
- Before repeating any review/audit command (`/simplify`, CLAUDE.md audit, etc.), confirm something actually changed since the last run (`git log`/`git status`/diff the target file) — re-running against identical state just repeats prior output.
- Not every altitude/reuse finding is a net improvement — verify the concrete before/after, not just the abstract principle. A `/simplify` round once "fixed" an altitude finding by adding `display.py::parse_geometry()`, but the next round's simplification pass caught that it made things worse (stringified a known constant, `WINDOW_SIZE`, just to re-parse it) and it was reverted. When a fix only has one call site, weigh the actual lines saved/added, not just "is this more general."
- Cross-function consistency of derived/normalized values is a recurring bug source here: `ui_logic.py` had two functions independently deciding what to do with the same raw `Content-Type` header (one normalized case/params, the other didn't), causing a real filename-extension bug. When two functions read the same external input, check whether they normalize it the same way before assuming they're both correct.
- **Accepted SSRF limitation** (`ui_logic.py::is_fetchable_url`): URL/redirect validation only checks scheme (`http`/`https`) and presence of a host — it does not resolve the hostname or block loopback/link-local/private IP ranges (e.g. `127.0.0.1`, `169.254.169.254`). This is a deliberate scope decision (confirmed with the user): the app is a single-user desktop GUI where the user supplies their own URL, so full SSRF hardening against the user's own reachable network was judged disproportionate. Don't re-flag this as a new finding in future audits.
