from markwright.core.exceptions import (
    CorruptFileError,
    InvalidPasswordError,
    OutputWriteError,
    UnsupportedFileError,
)

# Shared by the CLI and the interactive menu so both describe each domain error
# the same way. Keyed by ``type[Exception]`` because both look it up with whatever
# they caught.
ERROR_MESSAGE_KEYS: dict[type[Exception], str] = {
    UnsupportedFileError: "error.unsupported_file",
    InvalidPasswordError: "error.invalid_password",
    CorruptFileError: "error.corrupt_file",
    OutputWriteError: "error.output_write_failed",
}
