
import socket
from exceptions import P3Exception


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
        
    def send(self, msg: str) -> str:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.server_name,self.server_port))

        client_socket.send(msg.encode(encoding="utf-8"))
        response = client_socket.recv(1024).decode(encoding="utf-8")

        if response[:2] == "OK":
            return response[3:]
        elif response[:3] == "BYE":
            return None
        else:
            raise DSException(response[4:])

    def register(self, ):
        resp = self.send(" ".join(["REGISTER", self.nick, self.ip_address, self.port, self.password, self.protocol]))
        
    def query(self,nick):
        resp = self.send(" ".join(["QUERY", nick]))
        return resp.split(' ')[1:]
        
        
    def quit(self):
        self.send("QUIT")

class DSException(P3Exception):
    def __init__(self, msg=None):
        super().__init__()
        self.securebox_exception_msg = msg

    def __str__(self) -> str:
        return "Error: " + self.securebox_exception_msg


