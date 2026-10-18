"""An untrusted swap sent as an export-area file may not delete a requirer's
realm placement (issue #2600).

A file inside an export directory is the author's text by its path (issue
#2524): `revl_swap` compiles it under the authoring profile, exactly as if it
had been sent inline. Issue #2587 drives the realm-removal refusal through the
swap door with inline source; this module sends the same candidate as an
export-area file in `files`, and nothing else.

The candidate keeps every running component, adds a shared-realm provider of
`kv`, and leaves out TenantAApp's clause: refused by name, the refusal
pointing at the exported file, and the running composition untouched.
Controls: the same file placed by the operator outside the export area swaps
in under a trusted author, and an export-area file that keeps the clause
swaps in under the untrusted one.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from revl.mcp import server as server_mod  # noqa: E402
from test_untrusted_requirer_realm_swap_2587 import (  # noqa: E402,F401
    APP_HEADER, REFUSAL, _as_untrusted_author, _call, _full_candidate,
    _line_of, _messages, _realms, _running, clean_session, loaded, pytestmark)

REMOVED = ("admission refused: this author cannot remove the realm placement "
           "of `TenantAApp`: the admitted `isolate kv in realm(\"tenant_a\")` "
           "would move its `kv` requirement to the shared realm")


def _candidate(*, keep_app_clause: bool) -> str:
    """The full candidate as the untrusted author writes it."""
    return _as_untrusted_author(_full_candidate(keep_app_clause=keep_app_clause))


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _exported(base: Path, text: str) -> Path:
    """`text` as a file inside the root's export directory."""
    return _write(base / ".revl" / "export" / "tenants.rvl", text)


def _swap_files(path: Path) -> dict:
    return _call("revl_swap", {"files": [str(path)], "replacing": ["TenantAApp"]})


def test_untrusted_swap_of_an_exported_file_dropping_the_clause_is_refused(
        loaded):  # noqa: F811
    assert server_mod.AUTHORING.profile() is not None  # the untrusted author
    text = _candidate(keep_app_clause=False)
    exported = _exported(loaded.parent, text)
    swapped = _swap_files(exported)
    assert swapped["ok"] is False, swapped
    assert swapped.get("admitted") is False, swapped
    assert swapped.get("swapped") is False, swapped
    assert REFUSAL in _messages(swapped), swapped
    refusal = next(d for d in swapped["diagnostics"] if REFUSAL in d["message"])
    assert refusal["message"] == REMOVED, refusal
    assert refusal.get("code") == "G9", refusal
    # it points at the requirer, in the exported file
    assert refusal.get("file") == os.path.relpath(exported), refusal
    assert refusal.get("line") == _line_of(text, APP_HEADER), refusal
    assert _realms("TenantAApp") == {"kv": "tenant_a"}
    assert "SharedStore" not in _running()


def test_trusted_swap_of_the_same_file_outside_the_export_area_is_admitted(
        loaded):  # noqa: F811
    server_mod.set_authoring_trust(host_code=True)
    assert server_mod.AUTHORING.profile() is None
    placed = _write(loaded.parent / "candidate.rvl",
                    _candidate(keep_app_clause=False))
    swapped = _swap_files(placed)
    assert swapped["ok"] is True, swapped
    assert swapped.get("swapped") is True, swapped
    assert _realms("TenantAApp") == {}
    assert "SharedStore" in _running()


def test_untrusted_swap_of_an_exported_file_keeping_the_clause_is_admitted(
        loaded):  # noqa: F811
    assert server_mod.AUTHORING.profile() is not None
    exported = _exported(loaded.parent, _candidate(keep_app_clause=True))
    swapped = _swap_files(exported)
    assert swapped["ok"] is True, swapped
    assert swapped.get("swapped") is True, swapped
    assert _realms("TenantAApp") == {"kv": "tenant_a"}
    assert _realms("TenantAStore") == {"kv": "tenant_a"}
    assert "SharedStore" in _running()
