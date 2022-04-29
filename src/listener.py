from http import client
from multiprocessing import connection
import threading
import socket
from call_manager import User

from exceptions import P3Exception
from practica3_client import ClientApplication, VideoClient
from util import TCP

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
        server_socket = TCP.server_socket(self.client_app._tcp_port, max_connections=10)

        print(f"Listener esperando en el puerto: {self.client_app._tcp_port}")

        while 1:
            ##addr es tupla ()
            connection_socket, addr = server_socket.accept()
            
            petition = TCP.recvall(connection_socket).decode(encoding="utf-8")
            self.process_control_message(petition, connection_socket, addr[0])
            connection_socket.close() 

    def process_control_message(self, petition, connection_socket, addr):
        
        print(f"Proceso mensaje de control {petition}")
        
        petition_list = petition.split(' ')

        try: 
            msg, nick, udp_port = petition_list

            if msg == "CALLING":
                self.client_app.call_manager.receive_call(addr, connection_socket, nick, udp_port)
            elif msg == "CALL_ACCEPTED":
                self.client_app.call_manager.call_accepted(nick, udp_port)
        except ValueError:
            try:
                msg, nick = petition_list
                if msg == "CALL_DENIED":
                    self.client_app.call_manager.receive_call_denied(nick)
                elif msg == "CALL_END":
                    self.client_app.call_manager.receive_call_end(nick)
                elif msg == "CALL_HOLD":
                    self.client_app.call_manager.receive_call_hold(nick)
                elif msg == "CALL_RESUME":
                    self.client_app.call_manager.receive_call_resume(nick)
            except ValueError:
                msg = petition_list[0]
                if msg == "CALL_BUSY":
                    self.client_app.call_manager.receive_call_busy()

    def accept_call(self,ipaddr,tcp_port):
        print("Mando mensaje de accept")
        TCP.create_socket_and_send(f"{self.ACCEPT_MSG} {self.client_app.ds_client.nick} {self.client_app._udp_port}",ipaddr,tcp_port)

    def reject_call_busy(self, ipaddr,tcp_port):
        TCP.create_socket_and_send(self.BUSY_MSG,ipaddr,tcp_port)

    def reject_call(self, ipaddr,tcp_port):
        TCP.create_socket_and_send(self.BUSY_MSG,ipaddr,tcp_port)

    def check_ip(self,nick,addr):
        return self.client_app.ds_client.query(nick)[1]==str(addr) 

    def check_control_message(self, nick, addr, nick_addr):
        ''''Comprueba que el mensaje proviene del usuario 
            al que habias mandado CALLING'''

        #comprobar identidad
        if str(nick_addr)==str(addr):
            
            #comprobar si es la persona con la que estoy interactuando
            if self.client_app.in_call() or self.client_app.waiting_call_response():
                return nick==self.client_app.peer.nick

            return True

        return False

      

    

 
class WrongCallPetitionException(P3Exception):
    def __init__(self, msg=None):
        super().__init__()
        self.securebox_exception_msg = msg

    def __str__(self) -> str:
        return "Error: " + self.securebox_exception_msg

