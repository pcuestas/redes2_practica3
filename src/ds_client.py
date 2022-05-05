
from ipaddress import ip_address
import socket
from exceptions import DSException, P3Exception, SocketError
from util import TCP
import netifaces as ni

class DSClient():

    def __init__(
        self, 
        client_app,
        ip_address=socket.gethostbyname(socket.gethostname()), # tomar mi ip
        protocol="V0",
    ):
        # ds server:
        self.server_port = 8000
        self.server_name = "vega.ii.uam.es"

        self.nick = None
        self.password = None
        self.client_app = client_app

        self.contact_book = {}
        
        # descomentar las siguientes dos líneas para conectar con alguien en la vpn
        import netifaces as ni
        ip_address = ni.ifaddresses('tun0')[ni.AF_INET][0]['addr']
        self.ip_address = ip_address
        self.client_app = client_app
        self.protocol = protocol

        self.registered = False
        
    def send(self, msg: str) -> str:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((self.server_name, self.server_port))

        client_socket.send(msg.encode(encoding="utf-8"))
        response = TCP.recvall(client_socket).decode(encoding="utf-8")

        if response[:2] == "OK":
            return response[3:]
        elif response[:3] == "BYE":
            return None
        else:
            raise DSException(response[4:])

    def register(self):
        if self.registered:
            self.quit()
        print(f"Me registro con nick {self.nick}, ip {self.ip_address}, puerto {str(self.client_app._tcp_port)} y protocolo {self.protocol}")
        resp = self.send(" ".join(["REGISTER", self.nick, self.ip_address, str(self.client_app._tcp_port), self.password, self.protocol]))
        self.registered = True

    def query(self, nick):
        '''devuelve [nick, ip_address, port, protocols]'''

        not_found = True
        user = None

        if nick in self.contact_book.keys():
            user=self.contact_book[nick]
            not_found = False

            # Ver si la entrada está actualizada
            try:
                TCP.create_socket_and_send(" ",user[0],int(user[1]))

            #TODO: poner excepcion que es
            except Exception as e:
                print(e)
                not_found = True

        #entrada inexistente o desactualizada
        if not_found:
            resp = self.send(" ".join(["QUERY", nick]))
            resp = resp.split(' ')[1:] # [nick,ip_adress, port, prootocols]

            #update contact book
            self.contact_book[nick]=(resp[1],resp[2],resp[3])
            return resp
        
       
        return [nick,user[0],user[1],user[2]]
        
    def quit(self):
        self.send("QUIT")

    def list_users(self):
        '''devuelve una lista con elementos del tipo: [nick, ip_address, port, protocolo]'''
        resp_list = self.send("LIST_USERS")
        print(resp_list[:16])
        users= [
            query.split(' ') 
            for query in ' '.join(resp_list.split(' ')[2:]).split('#')[:-1]
        ]


        for user in users:
            try:
                self.contact_book[user[0]]=(user[1],user[2],user[3])
            except IndexError: #algún usuario se ha registrado sin todos los campos
                pass
        
        return users

    def remove_from_contact_book(self,nick):
        try:
            del self.contact_book[nick]
        except KeyError:
            pass


