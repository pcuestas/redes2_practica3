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
        TCP.create_socket_and_send(msg, sock)
        sock.close()

    def send(msg:str, sock):        
        try:
            sock.send(msg.encode(encoding="utf-8"))
        except OSError as e:
            raise SocketError(e)
            
    def recvall(sock):
        BUFF_SIZE = 4096 # 4 KiB
        data = b''
        while True:
            part = sock.recv(BUFF_SIZE)
            data += part
            if len(part) < BUFF_SIZE:
                break
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

