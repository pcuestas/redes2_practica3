from collections import deque
import threading
import socket
from exceptions import SocketError

#hilos 
class TerminatableThread(threading.Thread):

    def __init__(self):
        super().__init__()
        self.exit_event=threading.Event()

    def quit(self):
        pass

    def end(self):
       self.exit_event.set()
        

class TCP():
    def server_socket(tcp_port, max_connections):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('', tcp_port))
        server_socket.listen(max_connections)
        return server_socket

    def create_socket_and_send(msg:str, ip, tcp_port):
        print(f"ip {ip} y puerto {tcp_port} con tipos {type(ip)} y {type(tcp_port)}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, int(tcp_port)))
        TCP.send(msg, sock)
        sock.close()

    def send(msg:str, sock):        
        try:
            sock.send(msg.encode(encoding="utf-8"))
        except OSError as e:
            raise SocketError(e)
            
    def recvall(sock, timeout_seconds=1.0):
        BUFF_SIZE = 4096 # 4 KiB
        data = b''

        total_size_read = 0

        try:
            if timeout_seconds: 
                sock.settimeout(timeout_seconds)
            read = 1
            while read:
                part = sock.recv(BUFF_SIZE)
                data += part
                read = len(part)
                total_size_read += read
        except socket.error:
            pass
        
        sock.settimeout(None)
        print(f"Leído: {total_size_read}")
        return data

class CircularBuffer():
    def __init__(self, size):
        self.queue = deque(maxlen=size)
        self.size = size
        self.full = False

    def insert(self, elem):
        pass

def valid_port(port):
    return port>=1024 and port <65536

