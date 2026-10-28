"""Projects: a local folder where ideas become reviewed, reversible changes.

A project starts from a *specification* of an app (what it does, in words), never from
decompiled code. Anyone can add ideas in plain language; Claude turns an idea into a
proposed change; a person reviews the exact differences and approves or rejects it.
Nothing is applied without that approval, and every approval can be undone.
"""


class WorkspaceError(Exception):
    """`code` is an i18n key under `workspace.error.`."""

    def __init__(self, code: str, **params: object) -> None:
        super().__init__(code)
        self.code = code
        self.params = params
