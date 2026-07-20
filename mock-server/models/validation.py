from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValidationError:
    file: str
    line: int | None = None
    message: str = ""
    severity: str = "error"


@dataclass
class ValidationResult:
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, file: str, message: str, line: int | None = None):
        self.errors.append(ValidationError(file=file, line=line, message=message))

    def add_warning(self, file: str, message: str, line: int | None = None):
        self.warnings.append(ValidationError(file=file, line=line, message=message, severity="warning"))

    def merge(self, other: ValidationResult):
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
