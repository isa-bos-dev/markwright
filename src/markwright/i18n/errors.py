from markwright.core.exceptions import (
    ConversionError,
    CorruptFileError,
    InvalidPasswordError,
    OutputWriteError,
    UnsupportedFileError,
)

# Shared by the CLI and the GUI so both describe each domain error the same way.
ERROR_MESSAGE_KEYS: dict[type[ConversionError], str] = {
    UnsupportedFileError: "error.unsupported_file",
    InvalidPasswordError: "error.invalid_password",
    CorruptFileError: "error.corrupt_file",
    OutputWriteError: "error.output_write_failed",
}
