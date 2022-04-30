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
    '''
    Buffer circular FIFO con longitud máxima. 
    Si está lleno y se inserta un elemento, se sustituye el 
    primer elemento que se insertó.
    '''
    def __init__(self, maxlen):
        self._deque = deque(maxlen=maxlen)
        self._mutex = threading.Lock()
        self._len = 0

    def push(self, elem):
        '''Inserta un elemento a la cola FIFO'''
        with self._mutex:
            self._len = min(self._len + 1, self._deque.maxlen)
            self._deque.append(elem)

    def pop(self):
        '''Saca un elemento del buffer (el primero que se insertó) - FIFO'''
        if self._len:
            with self._mutex:
                self._len -= 1
                return self._deque.popleft()
        else:
            return None
    
    def full(self):
        '''True si está lleno, False si no.'''
        return self._len == self._deque.maxlen

    def empty(self):    
        '''True si está vacío, False si no.'''
        return self._len == 0

    def clear(self):
        '''Vacía el buffer'''
        self._len = 0
        self._deque.clear()
    
    def set_maxlen(self, maxlen):
        self._deque = deque(self._deque, maxlen=maxlen)
        self._len = min(self._len, maxlen)

    def __str__(self):
        return '(' + str(self._deque) + ', len='+ str(self._len) + ')'

def valid_port(port):
    return port >= 1024 and port < 65536

