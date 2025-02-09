
def recv_until(socket, buf_size: int = 1024, delimiter: str = "\r"):
    """
    Receive data from the socket until the delimiter is reached
    """
    edl = delimiter.encode()
    data = socket.recv(buf_size)
    i = data.find(edl)
    while i < 0:
        data += socket.recv(buf_size)
        i = data.find(edl)
    return data.decode()
