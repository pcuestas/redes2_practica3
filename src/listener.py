from http import client
from multiprocessing import connection
import threading
from socket import *
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

        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
        serverSocket.bind(('', self.client_app._tcp_port))
        serverSocket.listen(1)

        print(f"Listener esperando en el puerto: {self.client_app._tcp_port}")

        while 1:
            ##addr es tupla ()
            connection_socket, addr = serverSocket.accept()
            
            petition = TCP.recvall(connection_socket).decode(encoding="utf-8")
            self.process_control_message(petition, connection_socket,addr[0])
            connection_socket.close() 

    def process_control_message(self, petition, connection_socket, addr):
        
        print(f"Proceso mensaje de control {petition}")
        
        petition_list = petition.split(' ')

        try: 
            msg, nick, udp_port = petition_list
        except ValueError:
            try:
                msg, nick = petition_list
            except ValueError:
                msg = petition_list[0]
            
        udp_port=None

        nick, nick_addr, tcp_port, protocol= self.client_app.ds_client.query(nick)
            
        if msg =="CALLING" or msg=="CALL_ACCEPTED":
            peer = User(nick, nick_addr, udp_port, tcp_port)

        #if self.client_app.in_call() or self.client_app.awaiting_call():
            #self.reject_call(addr,tcp_port)
        
        if self.client_app.in_call() or True:
            #Procesar solo call_end, call_pause...

            if msg=="CALL_END":
                self.client_app.end_call()

        if self.client_app.waiting_call_response() or True:
            #Procesar solo call denied & call accepted

            if msg=="CALL_ACCEPTED":
                if not self.check_control_message(nick,addr,nick_addr):
                    print("Falla la comprobacion de mensaje")
                    return 
                print("Me han aceptado la llamada")
                self.client_app.init_call(peer)

            elif msg=="CALL_DENIED":
                self.client_app._waiting_call_response=False
                self.client_app.peer_nick=None

        if msg=="CALLING" and self.client_app.video_client.app.questionBox(
            title=f"Llamada entrante de {nick}",
            message="¿Aceptar llamada?"
        ):
            self.accept_call(addr,tcp_port)
            self.client_app.init_call(peer)

        #falta msg=="CALL_BUSY"
        
        else:
            self.reject_call(addr,tcp_port)

    def accept_call(self,ipaddr,tcp_port):
        print("Mando mensaje de accept")
        TCP.send(f"{self.ACCEPT_MSG} {self.client_app.ds_client.nick} {self.client_app._udp_port}",ipaddr,tcp_port)

    def reject_call_busy(self, ipaddr,tcp_port):
        TCP.send(self.BUSY_MSG,ipaddr,tcp_port)

    def reject_call(self, ipaddr,tcp_port):
        TCP.send(self.BUSY_MSG,ipaddr,tcp_port)

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

