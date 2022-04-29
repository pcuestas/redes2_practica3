from http import client
import threading
from tkinter import Image
from PIL import Image, ImageTk

import cv2
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

        self.peer = None

    def init_call(self, peer:User):
        
        #self.send_video_thread=SendVideoThread()
        #self.send_video_thread.start()
        self.peer=peer

        self.receive_video_thread=ReceiveVideoThread(self.client_app._udp_port, self.client_app)
        self.receive_video_thread.start()

        self.configure_send_socket()

    ## Cada pollTime se ejecuta. Mandar fotogramas al peer
    def send_data(self,data):
        if self.send_data_socket:
            # sendall ??
            self.send_data_socket.sendto(data,(self.peer.ipaddr,int(self.peer.udp_port)))
    
    def end_call(self):
        self.receive_video_thread.end()
        TCP.send(f"CALL_END {self.client_app.ds_client.nick}",
                 ip=self.client_app.peer.ipaddr,
                 tcp_port=self.client_app.peer.tcp_port)

        ##Mandar END_CALL al otro por TCP!!!!
        #self.send_video_thread.end()
        return

    def configure_send_socket(self):
        self.send_data_socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
       


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