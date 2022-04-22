from subprocess import check_call
import threading
import time
from socket import *


from exceptions import P3Exception
from appJar import gui
from practica3_client import ClientApplication


##Escucha peticiones de llamada y lanza hilos para procesar las peticiones
class ListenerThread(threading.Thread):

    BUSY_MSG="CALL_BUSY"
    
    # overriding constructor
    def __init__(self,video_client,serverPort=12000):
        # calling parent class constructor
        super().__init__()
        self.serverPort=serverPort
        self.proccess_call_thread=None 
        self.video_client=video_client
        self.in_call=False

    def run(self):
        print("Listener waiting in port : ", self.serverPort)

        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.bind(('', self.serverPort))
        serverSocket.listen(1)
        print("Servidor preparado para recibir")

        while 1:
            connectionSocket, addr = serverSocket.accept()
            petition = connectionSocket.recv(1024).decode(encoding="utf-8")

            if self.in_call:
                connectionSocket.send(self.BUSY_MSG.encode(encoding="utf-8"))
                connectionSocket.close()
            else:
                self.in_call=True
                self.proccess_call_thread=ProcessCallThread(petition,connectionSocket,self.video_client)
                self.proccess_call_thread.start()

            

    def get_in_call(self):
        return self.in_call

 
       



class WrongCallPetitionException(P3Exception):
    def __init__(self, msg=None):
        super().__init__()
        self.securebox_exception_msg = msg

    def __str__(self) -> str:
        return "Error: " + self.securebox_exception_msg


class ProcessCallThread(threading.Thread):


    

    def __init__(self, petition,connectionSocket,video_client):
        # calling parent class constructor
        super().__init__()
        self.petition=petition
        self.connectionSocket=connectionSocket
        self.video_client=video_client
        try:
            self.msg, self.nick, self.port=self.petition.split(' ')
        except:
            self.msg=None

    def run(self):
        if self.process_call_petition():
            a=2

    def quit(self):
        ClientApplication().listener_thread.in_call=False

    def process_call_petition(self):
        if self.msg!="CALLING":
            return False

        self.connectionSocket.send("RECIBIDOOOO".encode(encoding="utf-8"))
        self.video_client.app.textBox("Llamada de {}, su puerto es {}".format(self.nick,self.port))

        self.connectionSocket.close()  
        return True             