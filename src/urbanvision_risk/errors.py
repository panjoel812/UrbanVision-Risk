from dataclasses import dataclass


@dataclass(slots=True)
class ProjectError(Exception):
    code: str
    message_zh: str
    message_en: str
    recovery_zh: str
    recovery_en: str
    context: str | None = None

    def __str__(self) -> str:
        lines = [
            f"[ERROR {self.code}] {self.message_zh}",
            self.message_en,
        ]
        if self.context:
            lines.append(f"Context / 上下文: {self.context}")
        lines.extend(
            [
                f"恢复方法 / Recovery: {self.recovery_zh}",
                self.recovery_en,
            ]
        )
        return "\n".join(lines)


def report_error(error: ProjectError, debug: bool = False) -> int:
    if debug:
        raise error
    print(error)
    return 1
