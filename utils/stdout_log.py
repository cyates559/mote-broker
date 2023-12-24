import sys
from dataclasses import dataclass
from functools import partial
from threading import Lock

CONTROL_SEQUENCE = "\033["
DELIMITER = "m"
RESET = f"{CONTROL_SEQUENCE}0{DELIMITER}"

FOREGROUND_SELECTOR = 3
BACKGROUND_SELECTOR = 4
BRIGHT_FOREGROUND_SELECTOR = 9
BRIGHT_BACKGROUND_SELECTOR = 10


@dataclass
class Format:
    selector: int
    effect: int

    def __post_init__(self):
        self.slug = f"{CONTROL_SEQUENCE}{self.selector}{self.effect}{DELIMITER}"


FOREGROUND_BLACK = Format(FOREGROUND_SELECTOR, 0)
FOREGROUND_RED = Format(FOREGROUND_SELECTOR, 1)
FOREGROUND_GREEN = Format(FOREGROUND_SELECTOR, 2)
FOREGROUND_YELLOW = Format(FOREGROUND_SELECTOR, 3)
FOREGROUND_BLUE = Format(FOREGROUND_SELECTOR, 4)
FOREGROUND_MAGENTA = Format(FOREGROUND_SELECTOR, 5)
FOREGROUND_CYAN = Format(FOREGROUND_SELECTOR, 6)
FOREGROUND_WHITE = Format(FOREGROUND_SELECTOR, 7)

lock = Lock()


def printf(fmt: Format, *args, end="\n", **kwargs):
    with lock:
        sys.stdout.write(fmt.slug)
        first = True
        for arg in args:
            if first:
                first = False
            else:
                sys.stdout.write(" ")
            sys.stdout.write(str(arg))
        first = True
        for key, arg in kwargs.items():
            if first:
                first = False
            else:
                sys.stdout.write(" ")
            sys.stdout.write(str(key))
            sys.stdout.write("=")
            sys.stdout.write(str(arg))
        sys.stdout.write(RESET)
        if end is not None:
            sys.stdout.write(end)
        sys.stdout.flush()


print_in_red = partial(printf, FOREGROUND_RED)
print_in_green = partial(printf, FOREGROUND_GREEN)
print_in_yellow = partial(printf, FOREGROUND_YELLOW)
print_in_blue = partial(printf, FOREGROUND_BLUE)
print_in_magenta = partial(printf, FOREGROUND_MAGENTA)
print_in_cyan = partial(printf, FOREGROUND_CYAN)
