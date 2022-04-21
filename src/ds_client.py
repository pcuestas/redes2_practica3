
from re import S
import socket


class DSClient():

    def __init__(
        self, 
        nick, 
        password,
        ip_address=socket.gethostbyname(socket.gethostname()), 
        port="11000", 
        protocol="V0",
    ):
        self.server_port = 8000
        self.server_name = "vega.ii.uam.es"
        self.nick = nick
        self.ip_address = ip_address
        self.port = port
        self.password = password 
        self.protocol = protocol

    def register(self, ):
        resp=self.send(" ".join(["REGISTER", self.nick, self.ip_address, self.port, self.password, self.protocol]))
        print(resp)
        
    def send(self, msg: str) -> str:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.server_name,self.server_port))
        client_socket.send(msg.encode(encoding="utf-8"))
        return client_socket.recv(1024).decode(encoding="utf-8")
        




