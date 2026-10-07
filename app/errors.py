"""Small set of actionable application errors, without sensitive details."""


class ValidationError(ValueError):
    """A field or identifier is invalid."""


class FieldValidationError(ValidationError):
    """Errores por campo, separados de su presentación y sin valores personales."""

    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__("Revisa los campos indicados.")


class DatabaseError(RuntimeError):
    """Database integrity or schema compatibility prevents an operation."""


class FileOperationError(RuntimeError):
    """An attachment cannot be safely accessed or written."""


class BackupError(RuntimeError):
    """Backup validation, creation or restoration failed."""
