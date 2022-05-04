import threading
import socket
from exceptions import P3Exception
from practica3_client import ClientApplication, VideoClient
from util import TCP
import numpy as np


##Escucha peticiones de llamada y lanza hilos para procesar las peticiones
class ListenerThread(threading.Thread):

    BUSY_MSG="CALL_BUSY"
    ACCEPT_MSG="CALL_ACCEPTED"

    # overriding constructor
    def __init__(self, client_app: ClientApplication, video_client: VideoClient):
        # calling parent class constructor
        super().__init__()
        self.client_app = client_app
        self.proccess_call_thread=None 
        self.video_client=video_client

    def run(self):
        while 1:
            try:
                server_socket = TCP.server_socket(self.client_app._tcp_port, max_connections=10)
                break 
            except P3Exception as e:
                print("Listener ha tenido un problema: " + str(e))
                self.client_app._tcp_port = np.random.randint(10000, 11000)
                self.client_app.ds_client.register()
                print(f"Listener selecciona otro puerto aleatorio: {self.client_app._tcp_port}")

        print(f"Listener esperando en el puerto: {self.client_app._tcp_port}")

        while 1:
            ##addr es tupla ()
            connection_socket, addr = server_socket.accept()
            
            petition = connection_socket.recv(2 << 12).decode(encoding="utf-8")

            # el call_manager procesa y cierra el socket 
            self.client_app.call_manager.process_control_message(petition, connection_socket, addr[0])



