def _exit(self, exc_type, exc_val, exc_tb):
    self.stop()

def default_manager(cls):
    cls.__enter__ = cls.start
    cls.__exit__ = _exit
    return cls
