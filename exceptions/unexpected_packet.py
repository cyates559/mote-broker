class UnexpectedPacketType(Exception):
    def __init__(self, packet):
        super().__init__(f"{packet} was not expected")
