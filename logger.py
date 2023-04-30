import traceback
from functools import cached_property


class Log:
    @cached_property
    def context(self):
        from brokers.broker import Broker

        return Broker.instance

    def info(self, *args, **kwargs):
        self.context.log_info(*args, **kwargs)

    def warn(self, *args, **kwargs):
        self.context.log_warn(*args, **kwargs)

    def debug(self, *args, **kwargs):
        self.context.log_debug(*args, **kwargs)

    def error(self, *args, **kwargs):
        self.context.log_error(*args, **kwargs)

    def traceback(self):
        message = traceback.format_exc()
        self.context.log_error(message)


log = Log()
