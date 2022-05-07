import socket
from exceptions import DSException
from util import TCP

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

        self.contact_book = {}
        
        # descomentar las siguientes dos líneas para conectar con alguien en la vpn. puede que haya que cambiar el valor de 'tun0'
        #import netifaces as ni
        #ip_address = ni.ifaddresses('tun0')[ni.AF_INET][0]['addr']
        self.ip_address = ip_address
        self.client_app = client_app
        self.protocol = protocol

        self.registered = False
        
    def send(self, msg: str) -> str:
        '''envía un mensaje al servidor y controla el posible error de retorno. Si va bien devuelve la cadena d'''
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.settimeout(15)
                client_socket.connect((self.server_name, self.server_port))

                client_socket.send(msg.encode(encoding="utf-8"))
                response = TCP.recvall(client_socket).decode(encoding="utf-8")

                if response[:2] == "OK":
                    return response[3:]
                elif response[:3] == "BYE":
                    return None
                else:
                    raise DSException(response[4:] if len(response) > 4 else "El servidor DS ha fallado.")
        except socket.error:
            raise DSException("No se pudo conectar con el servidor DS.")

    def register(self):
        if self.registered:
            self.quit()
            
        resp = self.send(" ".join(["REGISTER", self.nick, self.ip_address, str(self.client_app._tcp_port), self.password, self.protocol]))
        self.registered = True

    def query(self, nick):
        '''devuelve [nick, ip_address, port, protocols]'''

        not_found = True
        user = None

        if nick in self.contact_book.keys():
            user = self.contact_book[nick]
            not_found = False

            try: # Ver si la entrada está actualizada
                TCP.create_socket_and_send(" ",user[0],int(user[1]))
            except socket.error:
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
        
        users= [
            query.split(' ') 
            for query in ' '.join(resp_list.split(' ')[2:]).split('#')[:-1]
        ]

        # actualizar la cache
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


