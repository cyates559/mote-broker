import sys

from broker.broker import Broker

if __name__ == "__main__":
    kwargs = {}
    kw = None
    for arg in sys.argv[1:]:
        if kw:
            pass
        else:
            s = arg.split("=")
            c = len(s)
            if c == 2:
                name, val = s
                if name[:2] == "--":
                    name = name[2:]
                kwargs[name] = val
            else:
                raise SyntaxError("Should have exactly one '=' per argumint")
    Broker.start(**kwargs)
