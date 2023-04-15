class UnexpectedPacketType(Exception):
    def __init__(self, packet):
        super().__init__(f"{packet.name} was not expected")
