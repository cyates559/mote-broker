class ConnectionClosed(Exception):
    def __init__(self, client_id):
        super().__init__(f"{client_id} Disconnected")
