import threading
import socket
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

    def process_control_message(self, petition, connection_socket, addr=None):
        
        print(f"Proceso mensaje de control {petition}")
        
        petition_list = petition.split(' ')

        try: 
            msg, nick, udp_port = petition_list

            if msg == "CALLING":
                self.client_app.call_manager.receive_call(addr, connection_socket, nick, udp_port)
            
            elif msg == "CALL_ACCEPTED":
                self.client_app.call_manager.call_accepted(connection_socket, nick, udp_port)
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
                    self.client_app.call_manager.receive_call_busy(nick)

    
    def request_peer(self, msg, ip, tcp_port):
        print(f"ip {ip} y puerto {tcp_port} con tipos {type(ip)} y {type(tcp_port)}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, tcp_port))
        TCP.send(msg, sock)
        petition = TCP.recvall(sock, 20).decode(encoding="utf-8")
        self.process_control_message(petition, sock)
        sock.close()

      

    

 
class WrongCallPetitionException(P3Exception):
    def __init__(self, msg=None):
        super().__init__()
        self.securebox_exception_msg = msg

    def __str__(self) -> str:
        return "Error: " + self.securebox_exception_msg

