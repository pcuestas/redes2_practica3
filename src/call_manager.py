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
    def __init__(self, nick, ipaddr:str, udp_port:int, tcp_port:int):
        self.nick = nick
        self.ipaddr = ipaddr
        self.udp_port = udp_port
        self.tcp_port = tcp_port

class CallManager(object):

    def __init__(self, client_app):
        self.client_app = client_app
        #self.send_video_thread = None
        self.receive_video_thread = None
        self.send_data_socket = None

        # usuario con el que se está interaccionando
        self._in_call_mutex = threading.Lock()
        self._peer = None
        #Flags que indican si se está esperando llamada o en llamada 
        self._waiting_call_response = False
        self._in_call = False

    def init_call(self, peer: User):
        self.client_app.init_call_window()

        self.configure_send_socket()

        self.set_in_call(True)
        self.set_peer(peer)

        self.receive_video_thread = ReceiveVideoThread(
            self.client_app._udp_port, self.client_app)
        self.receive_video_thread.start()


    ## Cada pollTime se ejecuta. Mandar fotogramas al peer
    def send_datagram(self, videoframe):
        #TODO modificar para que se manden las cabeceras
        if self.send_data_socket:
            # sendall ??
            self.send_data_socket.sendto(videoframe,(self._peer.ipaddr,self._peer.udp_port))
    
    def end_call(self, send_end_call=True):

        self.client_app.end_call_window()

        self.receive_video_thread.end()
        self.send_data_socket.close()
        self.send_data_socket = None

        if send_end_call:
            try: 
                TCP.create_socket_and_send(
                    f"CALL_END {self.client_app.ds_client.nick}",
                    ip=self._peer.ipaddr,
                    tcp_port=self._peer.tcp_port
                )
            except P3Exception as e:
                pass
        
        self.set_peer(None)
        self.set_in_call(False)


    def configure_send_socket(self):
        self.send_data_socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

    # funciones llamadas por el listener
    def receive_call(self, ipaddr, sock, nick, udp_port):
        '''Recibo llamada de un usuario'''
        if self.in_call():
            TCP.send("CALL_BUSY", sock)
            return 

        nick, nickaddr, tcp_port, protocol = self.client_app.ds_client.query(nick)
        
        if nickaddr != ipaddr:
            return 

        try:
            if self.client_app.video_client.app.questionBox(
                title=f"Llamada entrante de {nick}",
                message="¿Aceptar llamada?"
            ):
                peer = User(nick, nickaddr, int(udp_port), int(tcp_port))
                TCP.send(f"CALL_ACCEPTED {self.client_app.ds_client.nick} {self.client_app._udp_port}", sock)
                self.init_call(peer)
            else:
                TCP.send(f"CALL_DENIED {self.client_app.ds_client.nick}", sock)
        except P3Exception as e:
            pass

    def call(self, peer):
        '''Llamar al usuario peer'''
        self.set_waiting_call_response(True)
        self.set_peer(peer)
        try:
            self.client_app.listener_thread.request_peer(
                f"CALLING {self.client_app.ds_client.nick} {self.client_app._udp_port}",
                peer.ipaddr,
                peer.tcp_port
            )
        except P3Exception as e :
            self.set_waiting_call_response(False)
            self.set_peer(None)
            self.video_client.app.infoBox("Info", f"No se pudo conectar con {peer.nick}.\n {e}")
            
    def call_accepted(self, sock, nick, udp_port):
        '''Me han aceptado llamada'''
        if self.in_call():
            # para evitar errores
            TCP.send("CALL_BUSY", sock)
            return 

        if not self.waiting_call_response():
            # no espero respuesta  o remitente incorrecto, ignoro mensaje
            return 

        # es justo de quien esperamos llamada:
        self.set_waiting_call_response(False)
        self._peer.udp_port = int(udp_port) 
        self.init_call(self._peer)

    def receive_call_denied(self, nick):
        if not self.waiting_call_response():
            # no espero respuesta o remitente incorrecto, ignoro mensaje
            return

        self.set_waiting_call_response(False)
        self.set_peer(None)
        self.client_app.video_client.app.infoBox("Info", f"{nick} ha rechazado la llamada.")

    def receive_call_busy(self, nick):
        if not self.waiting_call_response():
            # no espero respuesta o remitente incorrecto, ignoro mensaje
            return

        self.set_waiting_call_response(False)
        self.set_peer(None)
        self.client_app.video_client.app.infoBox("Info", f"{nick} está ocupado.")

    def receive_call_end(self, nick):
        if not self.in_call():
            # no estoy en llamada  o remitente incorrecto, ignoro mensaje
            return 
        
        self.end_call(False)
        self.client_app.video_client.app.infoBox("Info", f"{nick} ha colgado.")

    def receive_call_hold(self, nick):
        if not self.in_call():
            # no estoy en llamada  o remitente incorrecto, ignoro mensaje
            return 
        
        #TODO poner llamada en hold
        self.client_app.video_client.app.infoBox("Info", f"{nick} ha puesto la llamada en hold.")

    def receive_call_resume(self, nick):
        if not self.in_call():
            # no estoy en llamada  o remitente incorrecto, ignoro mensaje
            return 
        
        #TODO reanudar llamada
    

    #def correct_nick_addr(self, nick, ipaddr):
    #    return (nick == self._peer.nick) and (ipaddr == self._peer.ipaddr)

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
        #self._in_call_mutex.acquire()
        self._peer = peer
        #self._in_call_mutex.release()

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
            #TODO cabecera 
            video, client_address = self.server_sock.recvfrom(2 << 14)
        
            #if self.end_call(message) or self.exit_event.is_set():
            if self.exit_event.is_set():
                #TODO self.modify_subWindow("Call ended")
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
