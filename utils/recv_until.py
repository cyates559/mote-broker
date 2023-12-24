from socket import MSG_PEEK


def recv_until(socket, buf_size: int = 1024, delimiter: str = "\r"):
    """
    Receive data from the socket until the delimiter is reached
    """
    edl = delimiter.encode()
    peek = socket.recv(buf_size, MSG_PEEK)
    i = peek.find(edl)
    data = b""
    while i < 0:
        data += socket.recv(buf_size)
        peek = socket.recv(buf_size, MSG_PEEK)
        i = peek.find(edl)
    data += socket.recv(i + len(edl))
    return data.decode()
