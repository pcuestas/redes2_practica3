from queue import PriorityQueue, Empty
import threading
import socket
from exceptions import SocketError

#hilos 
class TerminatableThread(threading.Thread):

    def __init__(self):
        super().__init__()
        self._exit_event=threading.Event()

    def quit(self):
        pass

    def end(self):
       self._exit_event.set()
    
    def stopped(self):
        return self._exit_event.is_set()
        

class TCP():
    def server_socket(tcp_port, max_connections):
        '''Crea y devuelve un socket tcp para ser usado como servidor'''
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('', tcp_port))
            server_socket.listen(max_connections)
            return server_socket
        except socket.error as err:
            raise SocketError(err)

    def create_socket_and_send(msg:str, ip, tcp_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            sock.connect((ip, int(tcp_port)))
            TCP.send(msg, sock)

    def send(msg:str, sock):        
        try:
            sock.send(msg.encode(encoding="utf-8"))
        except OSError as e:
            raise SocketError(e)
            
    def recvall(sock:socket.socket, timeout_seconds=0.5):
        BUFF_SIZE = 4096 # 4 KiB
        data = b''

        try:
            if timeout_seconds: 
                old_timeout = sock.gettimeout()
                sock.settimeout(timeout_seconds)

            part = b'0' # (porque no hay do while)

            while len(part):
                part = sock.recv(BUFF_SIZE)
                data += part
                
        except socket.error:
            pass
        
        if timeout_seconds: 
            sock.settimeout(old_timeout)

        return data
        
class CircularBuffer():
    '''
    Buffer circular FIFO con longitud máxima. 
    Recibe en el método push una dupla: (prioridad, data).
    Si está lleno y se inserta un elemento, y se sustituye el 
    primer elemento que se insertó.
    '''
    def __init__(self, maxsize):
        self._queue = PriorityQueue()
        self._maxsize = maxsize

    def push(self,elem):
        '''
        Inserta un elemento a la cola FIFO: 
        elem=(priority,data)
        '''
        if len(self._queue.queue) == self._maxsize:
            try:
                self._queue.get(block=False)
            except Empty:
                pass 
        self._queue.put(elem)

    def pop(self):
        '''
        Saca un elemento del buffer (el primero que se insertó) - FIFO
        Devuelve la dupla (prioridad, data) en caso de que no esté vacío
        el buffer. Devuelve None si está vacío.
        '''
        try:
            return self._queue.get(block=False)
        except:
            return None
    
    def full(self):
        '''True si está lleno, False si no.'''
        return len(self._queue.queue) == self._maxsize

    def empty(self):    
        '''True si está vacío, False si no.'''
        return not len(self._queue.queue)

    def clear(self):
        '''Vacía el buffer'''
        self._queue = PriorityQueue()
    
    def set_maxsize(self, maxsize):
        self._maxsize = maxsize
        if len(self._queue.queue) > maxsize:
            for _ in range(len(self._queue.queue) - maxsize):
                self._queue.get(block=False)
    
    @property
    def len(self):
        return len(self._queue.queue)

    def __str__(self):
        return \
              '(' + str(self._queue.queue)              \
            + ', len='+ str(len(self._queue.queue))     \
            + ', maxsize=' + str(self._maxsize)         \
            + ')'

def valid_port(port):
    return port >= 1024 and port < 65536

