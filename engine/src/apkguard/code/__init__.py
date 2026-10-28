"""Code understanding: what an APK's code can do, where, and a readable view of it."""

class CodeError(Exception):
    """`code` is an i18n key under `code.error.`."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
