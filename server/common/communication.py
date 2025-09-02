# read_n lee exactamente n bytes del socket
def read_n(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("short read")
        data += chunk
    return data

# write_all escribe todos los datos en el socket
def write_all(sock, data):
    total = 0
    while total < len(data):
        sent = sock.send(data[total:])
        if sent == 0:
            raise ConnectionError("short write")
        total += sent
