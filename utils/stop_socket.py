from socket import SOCK_STREAM, AF_INET, socket


def stop_socket(host: str, port: int):
    try:
        socket(AF_INET, SOCK_STREAM).connect((host, port))
    except:
        pass
