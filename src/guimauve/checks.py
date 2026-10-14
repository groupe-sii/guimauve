from dataclasses import dataclass


@dataclass(frozen=True)
class CheckFailure:
    check: str
    message: str


class EnvironmentCheckError(RuntimeError):
    def __init__(self, failures: list[CheckFailure]):
        self.failures = failures

        count = len(failures)
        title = f"Environment checks failed ({count} failure{'s' if count > 1 else ''}):"
        body = "\n".join(f"  - {f.check}: {f.message}" for f in failures)

        super().__init__(f"\n\n{title}\n{body}")
