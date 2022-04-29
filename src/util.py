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
    def send(msg, ip, tcp_port):
        try:
            print(f"ip {ip} y puerto {tcp_port} con tipos {type(ip)} y {type(tcp_port)}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, int(tcp_port)))

            sock.send(msg.encode(encoding="utf-8"))
            sock.close()
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

