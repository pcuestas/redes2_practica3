import socket
from exceptions import P3Exception
from practica3_client import ClientApplication, VideoClient
from util import TCP, TerminatableThread
import numpy as np

##Escucha peticiones de llamada y lanza hilos para procesar las peticiones
class ListenerThread(TerminatableThread):

    def __init__(self, client_app: ClientApplication, video_client: VideoClient):
        super().__init__()
        self.client_app = client_app
        self.proccess_call_thread=None 
        self.video_client=video_client

    def run(self):
        while 1:
            try:
                server_socket = TCP.server_socket(self.client_app._tcp_port, max_connections=10)
                server_socket.settimeout(1.0)
                break 
            except P3Exception as e:
                self.register_with_new_port(e)

        print(f"Listener esperando en el puerto: {self.client_app._tcp_port}")
    
        while not self.stopped():
            try:
                connection_socket = None
                connection_socket, addr = server_socket.accept() # addr es tupla ()
                
                connection_socket.settimeout(1.0)
                petition = connection_socket.recv(2 << 12).decode(encoding="utf-8")
            except socket.timeout:
                if connection_socket:
                    connection_socket.close()
                continue #ignorar

            # el call_manager procesa y cierra el socket 
            self.client_app.call_manager.process_listener_message(petition, connection_socket, addr[0])

        # liberar recursos
        server_socket.close()
    
    def register_with_new_port(self, e:P3Exception):
        print("Listener ha tenido un problema: " + str(e))
        self.client_app._tcp_port = np.random.randint(10000, 11000)
        self.client_app.ds_client.register()
        print(f"Listener selecciona otro puerto aleatorio para tcp, el otro estaba ocupado. Nuevo puerto: {self.client_app._tcp_port}")
