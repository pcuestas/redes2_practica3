from http import client
from re import I
import threading
from tkinter import Image
from PIL import Image, ImageTk

import cv2
from exceptions import P3Exception
import numpy as np
from util import TCP, CircularBuffer, TerminatableThread
import time
import socket

HEADER_ITEMS=4

class User(object):
    def __init__(self, nick, ipaddr:str, udp_port:int, tcp_port:int):
        self.nick = nick
        self.ipaddr = ipaddr
        self.udp_port = udp_port
        self.tcp_port = tcp_port


class CallManager(object):

    def __init__(self, client_app):
        self.client_app = client_app
        #self.consume_video_thread = None
        self.receive_video_thread = None
        self.receive_control_commands_thread = None
        self.send_data_socket = None

        # usuario con el que se está interaccionando
        self._in_call_mutex = threading.Lock()
        self._peer = None
        #Flags que indican si se está en llamada/pausa 
        self._in_call = False
        self._pause = False
        self._can_i_resume = False

        #gestión de flujo
        self._receive_fps = 0
        self._send_fps = None
        self._send_order_number = None
        self._resolution = None
        self._last_frame_shown = -1
            #TODO buffer de frames
        self.call_buffer = CircularBuffer(100)

    def init_call(self, peer: User, control_sock:socket.socket):
        self.client_app.init_call_window()
  
        # fps y resolución por defecto
        self.set_send_fps()
        self.set_image_resolution()
        self.reset_variables()
        #TODO preguntar: self.client_app.video_client.set_video_capture(False)

        self._send_order_number = 0

        self.configure_send_socket()

        self.set_in_call(True)
        self.set_peer(peer)
        self._pause = False

        # lanzar los hilos de la llamada
        self.receive_video_thread = ReceiveVideoThread(
            self.client_app._udp_port, self.client_app
        )
        self.receive_video_thread.start()

        self.receive_control_commands_thread = ReceiveControlCommandsThread(
            control_sock, self
        )
        self.receive_control_commands_thread.start()

        #self.consume_video_thread = ConsumeVideoThread(
        #    self.client_app, self, self.call_buffer
        #)
        #self.consume_video_thread.setDaemon(True)
        #self.consume_video_thread.start()

    def reset_variables(self):
        self.call_buffer.clear()
        self._last_frame_shown = -1
        self._in_call = False
        self._pause = False
        self._can_i_resume = False

    ## Cada pollTime se ejecuta. Mandar fotogramas al peer
    def send_datagram(self, videoframe):
        if self.send_data_socket and not self._pause and self._in_call:
            header = self.build_header()
            self.send_data_socket.sendto(header+videoframe,(self._peer.ipaddr, self._peer.udp_port))
            self._send_order_number += 1

    def build_header(self):
        'Construye la cabcera y la devuelve como una cadena de bytes'
        return bytes(str(self._send_order_number)+"#"+str(time.time())+"#" \
                + self.resolution_str()+"#"+str(self._send_fps)+"#",'utf-8')

    def resolution_str(self):
        if self._resolution == "LOW":
            return str(160) + 'x' + str(120)
        if self._resolution == "MEDIUM":
            return str(320) + 'x' + str(240)
        if self._resolution == "HIGH":
            return str(640) + 'x' + str(480)

    def set_send_fps(self, fps=25):
        self._send_fps = int(fps)
        self.client_app.video_client.app.setPollTime(int(1000 // fps))
        self.client_app.video_client.update_status_bar(self._resolution, self._send_fps)

    def set_image_resolution(self, resolution="MEDIUM"):
        self._resolution = resolution
        self.client_app.video_client.setImageResolution(resolution)
        self.client_app.video_client.update_status_bar(self._resolution, self._send_fps)

    def end_call(self, send_end_call=True, message=None):
        self.set_in_call(False)

        if message: self.client_app.video_client.app.infoBox("Info", message)

        self.client_app.end_call_window()

        if send_end_call:
            try: 
                self.send_control_msg(
                    f"CALL_END {self.client_app.ds_client.nick}"
                )
            except P3Exception as e:
                pass
        
        self.receive_video_thread.end()
        #TODO !!!!
        self.receive_video_thread.join(0.4)
        self.receive_video_thread = None

        self.receive_control_commands_thread.end()
        self.receive_control_commands_thread.join(0.7)
        self.receive_control_commands_thread = None

        #self.consume_video_thread.end()
        #self.consume_video_thread = None

        self.send_data_socket.close()
        self.send_data_socket = None
        self.set_peer(None)
        
   
    def hold_and_resume_call(self):
        #TODO try except para el send
        #resume call 
        if self._pause and self._can_i_resume:
            self._pause = False
            self._can_i_resume = False
            self.client_app.video_client.app.setButton("pause/resume","Pause")
            self.send_control_msg(f"CALL_RESUME {self.client_app.ds_client.nick}")
            #Cuando se pausa el video, vaciar el buffer
            self.call_buffer.empty()
            
        #pause call
        elif not self._pause: 
            self._pause = True
            self._can_i_resume = True
            self.client_app.video_client.app.setButton("pause/resume","Resume")
            self.send_control_msg(f"CALL_HOLD {self.client_app.ds_client.nick}")

    def configure_send_socket(self):
        self.send_data_socket=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

    def quit(self):
        #TODO matar hilos, esta función se llama cuando la app se cierra
        if self.in_call():
            self.end_call()

    def send_control_msg(self, msg:str):
        try:
            TCP.send(msg, self.receive_control_commands_thread.control_socket)
        except P3Exception as e:
            pass

    # funciones llamadas por el listener
    def receive_call(self, ipaddr, sock, nick, udp_port):
        '''Recibo llamada de un usuario'''
        if self.in_call():
            print("Mando CALL_BUSY")
            TCP.send("CALL_BUSY", sock)
            sock.close()
            return 

        nick, nickaddr, tcp_port, protocol = self.client_app.ds_client.query(nick)
        
        if nickaddr != ipaddr:
            print(f"Fallan ips {nickaddr}=={ipaddr}")
            #TODO return 

        try:
            if self.client_app.video_client.app.questionBox(
                title="Llamada",
                message=f"¿Aceptar llamada entrante de {nick}?"
            ):
                peer = User(nick, nickaddr, int(udp_port), int(tcp_port))
                TCP.send(f"CALL_ACCEPTED {self.client_app.ds_client.nick} {self.client_app._udp_port}", sock)
                self.init_call(peer, sock)
            else:
                TCP.send(f"CALL_DENIED {self.client_app.ds_client.nick}", sock)
                sock.close()
        except P3Exception as e:
            pass

    def call(self, peer):
        '''Llamar al usuario peer'''
        if self.in_call():
            return #TODO mansaje 

        self.set_peer(peer)
        try:
            self.make_call(
                f"CALLING {self.client_app.ds_client.nick} {self.client_app._udp_port}",
                peer.ipaddr,
                peer.tcp_port
            )
        except P3Exception as e :
            self.set_peer(None)
            self.client_app.video_client.app.infoBox("Info", f"No se pudo conectar con {peer.nick}.\n {e}")
    
    def call_accepted(self, sock, nick, udp_port):
        '''Me han aceptado llamada'''
        if self.in_call():
            # para evitar errores
            TCP.send("CALL_BUSY", sock)
            sock.close()
            return 

        self._peer.udp_port = int(udp_port) 
        self.init_call(self._peer, sock)

    def receive_call_denied(self, nick, sock):
        
        sock.close()

        self.set_peer(None)
        self.client_app.video_client.app.infoBox("Info", f"{nick} ha rechazado la llamada.")

    def receive_call_busy(self, sock):
        
        sock.close()

        nick = self._peer.nick
        self.set_peer(None)
        self.client_app.video_client.app.infoBox("Info", f"{nick} está ocupado.")

    def receive_call_end(self, nick):
        if not self.in_call():
            # no estoy en llamada, ignoro mensaje
            return 
        
        self.end_call(False)
        self.client_app.video_client.app.infoBox("Info", f"{nick} ha colgado.")

    def receive_call_hold(self, nick):
        if not self.in_call():
            # no estoy en llamada, ignoro mensaje
            return 
        
        self._can_i_resume = False
        self._pause = True
        
        self.client_app.video_client.app.infoBox(
            "Info", 
            f"{nick} ha puesto la llamada en hold.", 
            parent="CallWindow"
        )

    def receive_call_resume(self, nick):
        if not self.in_call():
            # no estoy en llamada, ignoro mensaje
            return 
        self._pause = False
        self._can_i_resume = False

    # getters y setters de atributos
    def set_in_call(self, val):
        with self._in_call_mutex:
            self._in_call = val

    def in_call(self):
        with self._in_call_mutex:
            val = True == self._in_call
            return val

    def set_peer(self, peer):
        self._peer = peer

    def peer(self):
        return self._peer
    
    # mensajes de control
    def make_call(self, msg, ip, tcp_port):
        '''
            Llama a un usuario y gestiona la llamada.
            msg="CALLING nick udpport", 
            ip= la ip del usuario
            tcp_port= el puerto de control del usuario al que se llama
        '''
        try:
            control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            control_sock.settimeout(20) # 20 segundos esperando llamada, no más
            
            control_sock.connect((ip, tcp_port))            
            TCP.send(msg, control_sock)
            answer_msg = control_sock.recv(2 << 12).decode(encoding="utf-8")

            self.process_control_message(answer_msg, control_sock)  

        except socket.error:
            raise P3Exception("El usuario no ha respondido a la llamada.")

    def process_control_message(self, petition, connection_socket=None, addr=None):
        
        print(f"Call manager procesa: '{petition}'")
        
        petition_list = petition.split(' ')

        try: 
            msg, nick, udp_port = petition_list

            if msg == "CALLING":
                self.receive_call(addr, connection_socket, nick, udp_port)
            
            elif msg == "CALL_ACCEPTED":
                self.call_accepted(connection_socket, nick, udp_port)
        except ValueError:
            try:
                msg, nick = petition_list
                if msg == "CALL_DENIED":
                    self.receive_call_denied(nick, connection_socket)
                elif msg == "CALL_END":
                    self.receive_call_end(nick)
                elif msg == "CALL_HOLD":
                    self.receive_call_hold(nick)
                elif msg == "CALL_RESUME":
                    self.receive_call_resume(nick)
            except ValueError:
                msg = petition_list[0]
                if msg == "CALL_BUSY":
                    self.receive_call_busy(connection_socket)



class ReceiveVideoThread(TerminatableThread):
    def __init__(self, udp_port, client_app):
        super().__init__()
        self.server_port = udp_port
        self.client_app = client_app
        self.call_manager = client_app.call_manager
        self.call_buffer = self.client_app.call_manager.call_buffer
        self.fps = 25 # valor inicial, no importa mucho

    def run(self):

        self.configure_socket()
        pause = True
        cummulative_time = 0
        while 1:
            try:
                self.server_sock.settimeout(1/self.fps)
                data, client_address = self.server_sock.recvfrom(2 << 14)

                order_number,timestamp,resolution,fps,compressed_frame = self.split_data(data)

                self.insert_in_buffer(compressed_frame, int(order_number), float(timestamp), resolution, fps)
                cummulative_time = 0
            except (socket.timeout, ValueError):

                if self.client_app.call_manager._pause:
                     cummulative_time =0
                else:
                    cummulative_time += 1/self.fps
              

            if cummulative_time > 3:
                self.call_manager.end_call(message="Se ha cortado la llamada por fallos en la conexión")
                self.quit()
                return 
            
            if self.stopped():
                #TODO self.modify_subWindow("Call ended")
                self.quit()
                return

            if pause: 
                if self.call_buffer.len < self.fps / 2:
                    pause = False 
                else:
                    continue

            while self.call_buffer.len > (self.fps / 2) > 0:
                print("Quito del buffer, hay demasiados")
                self.call_buffer.pop()

            try:
                self.call_manager._last_frame_shown, fts, resolution, fps, frame = self.call_buffer.pop()

                self.client_app.video_client.app.setImageData("inc_video", frame, fmt='PhotoImage')

                if self.fps != fps: self.set_receive_fps(fps)
                
                self.client_app.video_client.app.setLabel("CallInfo", f"Recibiendo datos a {self.fps} fps; resolución: {resolution.decode()}.")
    
            except (TypeError):
                #buffer vacio
                pause = True
                pass


    def set_receive_fps(self, fps):
        self.fps = fps
        self.call_buffer.set_maxsize(int(fps//2)) # 0.5 segundos de vídeo en el buffer
    
    def split_data(self,data):
        'Devuelve una lista con los elementos de la cabecera y los datos del video'
        #cabecera: Norden#TimeStamp#Resolution#FPS#
        return data.split(b'#', HEADER_ITEMS)

    def configure_socket(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(('', self.server_port))

    def end(self):
        super().end()
        # despertar al hilo de recv si fuera necesario
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            s.sendto(b'1',(self.client_app.ds_client.ip_address, self.server_port))

    

    def insert_in_buffer(self, compressed_frame, order_number:int, timestamp, resolution, fps):
        'Inserta en el buffer una tupla (n_orden,frame descompriido) mientras no sea un frame antiguo'
        if order_number > self.client_app.call_manager._last_frame_shown:
        #TODO tener en cuenta la resolución para hacer resize !!!!!!!! la resolucion es STRING o pixles
            decimg = cv2.imdecode(np.frombuffer(compressed_frame,np.uint8), 1)
            cv2_im = cv2.cvtColor(decimg,cv2.COLOR_BGR2RGB)
            img_tk = ImageTk.PhotoImage(Image.fromarray(cv2_im))
            self.client_app.call_manager.call_buffer.push((order_number, float(timestamp), resolution, int(fps), img_tk))
      

    def quit(self):
        self.server_sock.close()
        print("Hilo que recibe acaba")

class ReceiveControlCommandsThread(TerminatableThread):
    def __init__(self, control_socket:socket.socket, call_manager: CallManager):
        super().__init__()
        self.control_socket = control_socket
        self.call_manager = call_manager

    def run(self):
        self.control_socket.settimeout(0.5)
        while 1:
            try:
                msg = self.control_socket.recv(2 << 15).decode(encoding="utf-8")
                if len(msg) > 0:
                    self.call_manager.process_control_message(msg)
            except socket.timeout:
                pass
            finally: # para el timeout
                if self.stopped():
                    self.quit()
                    return

    def quit(self):
        self.control_socket.close()
        print("Hilo de recepción de control acaba")

class ConsumeVideoThread(TerminatableThread):
    def __init__(self, client_app, call_manager:CallManager, callbuf:CircularBuffer):
        super().__init__()
        self.call_manager = call_manager
        self.client_app = client_app
        self.call_buffer = callbuf
        self.fps = 25 # valor inicial, no importa mucho

        self.prev_fts = time.time() # timestamp del frame anterior
        self.prev_ts = time.time() #timestamp del útimo momento en el que se mostró un frame

    def run(self):
        pause = True # indica si hay que esperar a que se llene un poco el buffer

        while 1:
            
            if self.stopped():break
            
            #while pause:
            #    time.sleep(1/(2*self.fps))
            #    if self.stopped():break
            #    pause = (self.call_buffer.len < (self.fps))

            #if self.stopped():break

            

        self.quit()

    def quit(self):
        print("Hilo que consume frames acaba")