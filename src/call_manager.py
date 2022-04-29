from http import client
import threading
from tkinter import Image
from PIL import Image, ImageTk

import cv2
from exceptions import P3Exception
import numpy as np
from util import TCP, TerminatableThread
import time
import socket

class User(object):
    def __init__(self, nick, ipaddr, udp_port, tcp_port):
        self.nick = nick
        self.ipaddr = ipaddr
        self.udp_port = udp_port
        self.tcp_port = tcp_port

class CallManager(object):

    def __init__(self, client_app):
        self.client_app = client_app
        #self.send_video_thread = None
        self.receive_video_thread = None
        self.send_data_socket=None

        # usuario con el que se está interaccionando
        self._in_call_mutex = threading.Lock()
        self._peer = None
        #Flags que indican si se está esperando llamada o en llamada 
        self._waiting_call_response = False
        self._in_call = False

    def init_call(self, peer:User):
        self.configure_send_socket()

        self.set_in_call(True)
        self.set_peer(peer)

        self.receive_video_thread=ReceiveVideoThread(self.client_app._udp_port, self.client_app)
        self.receive_video_thread.start()


    ## Cada pollTime se ejecuta. Mandar fotogramas al peer
    def send_data(self,data):
        #TODO modificar para que se manden las cabeceras
        if self.send_data_socket:
            # sendall ??
            self.send_data_socket.sendto(data,(self.peer.ipaddr,int(self.peer.udp_port)))
    
    def end_call(self):
        self.receive_video_thread.end()

        TCP.create_socket_and_send(f"CALL_END {self.client_app.ds_client.nick}",
                 ip=self.client_app.peer.ipaddr,
                 tcp_port=self.client_app.peer.tcp_port)
        
        self.set_peer(False)
        self.set_in_call(False)

        return

    def configure_send_socket(self):
        self.send_data_socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

    # funciones llamadas por el listener
    def receive_call(self, ipaddr, sock, nick, udp_port):
        if self.in_call():
            TCP.send("CALL_BUSY", sock)
            return 

        nick, nickaddr, tcp_port, protocol = self.client_app.ds_client.query(nick)

        if self.client_app.video_client.app.questionBox(
            title=f"Llamada entrante de {nick}",
            message="¿Aceptar llamada?"
        ):
            peer = User(nick, nickaddr, udp_port, tcp_port)
            TCP.send(f"CALL_ACCEPTED {self.client_app.ds_client.nick} {self.client_app._udp_port}", sock)
            self.init_call(peer)
        else:
            TCP.send(f"CALL_DENIED {self.client_app.ds_client.nick}", sock)

    def call(self, peer):
        self.set_waiting_call_response(True)
        self.set_peer(peer)
        try:
            TCP.create_socket_and_send(f"CALLING {self.ds_client.nick} {self._udp_port}",peer.ipaddr,int(peer.tcp_port))
        except P3Exception as e :
            self.set_waiting_call_response(False)
            self.set_peer(None)
            self.video_client.app.infoBox("Info", f"No se pudo conectar con {peer.nick}.\n {e}")
            
    def call_accepted(self, nick, udp_port):
        pass

    # getters y setters de atributos protegidos por mutex
    def set_waiting_call_response(self, val):
        self._in_call_mutex.acquire()
        try:
            self._waiting_call_response = val 
        finally:
            self._in_call_mutex.release()

    def waiting_call_response(self):
        self._in_call_mutex.acquire()
        val = True == self._waiting_call_response
        self._in_call_mutex.release()
        return val

    def set_in_call(self, val):
        self._in_call_mutex.acquire()
        self._in_call = val
        self._in_call_mutex.release()

    def in_call(self):
        self._in_call_mutex.acquire()
        val = True == self._in_call
        self._in_call_mutex.release()
        return val

    def set_peer(self, peer):
        self._in_call_mutex.acquire()
        self._peer = peer
        self._in_call_mutex.release()

    def peer(self):
        return self._peer
       


class ReceiveVideoThread(TerminatableThread):
    def __init__(self,udp_port, client_app):
        super().__init__()
        self.server_port=udp_port
        self.client_app = client_app

    def run(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_sock.bind(('', self.server_port))

        while 1:
            # ? cabecera 
            video, client_address = self.server_sock.recvfrom(4096)
        
            #if self.end_call(message) or self.exit_event.is_set():
            if self.exit_event.is_set():
                self.modify_subWindow("Call ended")
                self.quit()
                return


            #print("Recibo {}".format(message.decode()))
            self.modify_subWindow(video)

        

    def modify_subWindow(self,video):
        decimg = cv2.imdecode(np.frombuffer(video,np.uint8), 1)
        cv2_im = cv2.cvtColor(decimg,cv2.COLOR_BGR2RGB)
        img_tk = ImageTk.PhotoImage(Image.fromarray(cv2_im))
        #self.client_app.video_client.app.setLabel("msg_call_window", msg)
        self.client_app.video_client.app.setImageData("inc_video", img_tk, fmt='PhotoImage')
    

    def quit(self):
        self.server_sock.close()
        print("Hilo que recibe acaba")

    def end_call(self, message):
        return message.decode()[:8]=="CALL_END"



class SendVideoThread(TerminatableThread):
    def __init__(self, peer_port, peer_ip, client_app):
        super().__init__()
        self.server_port=peer_port
        self.server_name=peer_ip
        self.socket
        self.client_app=client_app

    def run(self):

        self.socket=socket(socket.AF_INET, socket.SOCK_DGRAM)
        i=0
        while not self.exit_event.is_set():
            message="{}".format(i).encode()
            self.socket.sendto(message,(self.server_name, self.server_port))
            time.sleep(1)
            i+=1

        self.quit()
   
    def quit(self):
        self.socket.close()
        print("Hilo que envia finaliza correctamente")