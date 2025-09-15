import dataclasses
import traceback
from contextlib import contextmanager
from functools import partial

from utils.stdout_log import print_in_yellow, print_in_green, print_in_red, print_in_magenta


@dataclasses.dataclass
class Logger:
    log_info: callable = print_in_green
    log_debug: callable = partial(print_in_magenta, "[DEBUG]")
    log_warn: callable = partial(print_in_yellow, "[WARN]")
    log_error: callable = partial(print_in_red, "[ERROR]")

    _contexts: list[dict] = dataclasses.field(default_factory=lambda: [{}])

    @contextmanager
    def context(self, **context):
        try:
            self._contexts.append({**self._contexts[-1], **context})
            yield self
        finally:
            self._contexts.pop()

    def info(self, *args, **kwargs):
        self.log_info(*args, **self._contexts[-1], **kwargs)

    def warn(self, *args, **kwargs):
        self.log_warn(*args, **self._contexts[-1], **kwargs)

    def debug(self, *args, **kwargs):
        self.log_debug(*args, **self._contexts[-1], **kwargs)

    def error(self, *args, **kwargs):
        self.log_error(*args, **self._contexts[-1], **kwargs)

    def traceback(self, *args, **kwargs):
        message = traceback.format_exc()
        self.log_error(message, *args, **kwargs)


log = Logger()
