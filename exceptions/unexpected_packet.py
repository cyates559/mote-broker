class UnexpectedPacketType(Exception):
    def __init__(self, packet):
        super().__init__(f"{packet.__class__.__name__} was not expected")
