import dataclasses
import traceback
from functools import partial

from utils.stdout_log import print_in_yellow, print_in_green, print_in_red, print_in_magenta


@dataclasses.dataclass
class Logger:
    log_info: callable = print_in_green
    log_debug: callable = partial(print_in_magenta, "[DEBUG]")
    log_warn: callable = partial(print_in_yellow, "[WARN]")
    log_error: callable = partial(print_in_red, "[ERROR]")

    def info(self, *args, **kwargs):
        self.log_info(*args, **kwargs)

    def warn(self, *args, **kwargs):
        self.log_warn(*args, **kwargs)

    def debug(self, *args, **kwargs):
        self.log_debug(*args, **kwargs)

    def error(self, *args, **kwargs):
        self.log_error(*args, **kwargs)

    def traceback(self):
        message = traceback.format_exc()
        self.log_error(message)


log = Logger()
