from datetime import timedelta
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
WIDTH = 640
HEIGHT = 480
MAX_FPS = 60
MIN_FPS = 10

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
        self.init_call_time = 0

        # usuario con el que se está interaccionando
        self._in_call_mutex = threading.Lock()
        self._peer = None
        #Flags que indican si se está en llamada/pausa 
        self._in_call = False
        self._pause = False
        self._can_i_resume = False
        self.frames_per_capture = 1
        self.prob_extra_frame = 0

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

        self.configure_send_socket()

        self.set_in_call(True)
        self.set_peer(peer)        
        self.init_call_time = time.time()

        # lanzar los hilos de la llamada
        self.receive_video_thread = ReceiveVideoThread(
            self.client_app._udp_port, self.client_app
        )
        self.receive_video_thread.setDaemon(True)
        self.receive_video_thread.start()

        self.receive_control_commands_thread = ReceiveControlCommandsThread(
            control_sock, self
        )
        self.receive_control_commands_thread.setDaemon(True)
        self.receive_control_commands_thread.start()

    def reset_variables(self):
        self.call_buffer.clear()
        self._last_frame_shown = -1
        self._in_call = False
        self._pause = False
        self._can_i_resume = False
        self._send_order_number = 0
        self.frames_per_capture = 1
        self.prob_extra_frame = 0

    def send_datagram(self, videoframe):
        '''Cada pollTime se llama. Mandar fotogramas al peer'''
        if self.send_data_socket and not self._pause and self._in_call:
            header = self.build_header()
            try:
                self.send_data_socket.sendto(header+videoframe,(self._peer.ipaddr, self._peer.udp_port))
                self._send_order_number += 1
            except socket.error:
                pass

    def build_header(self):
        '''Construye la cabcera y la devuelve como una cadena de bytes'''
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
        if fps > MAX_FPS or fps < MIN_FPS:
            self.client_app.video_client.app.infoBox("Error", f"Introduzca un número de fps entre {MIN_FPS} y {MAX_FPS}", parent="CallWindow")
            return        

        if self.client_app.video_client.using_webcam or self.client_app.video_client.screen_cap:
            self.client_app.video_client.resource_fps = fps

        #No podemos mandar más rapido de los fps del recurso
        send_fps = min(fps, self.client_app.video_client.resource_fps)

        #Si queremos mandar a menos frames, que los del recurso
        ratio_fps = self.client_app.video_client.resource_fps / send_fps
        self.frames_per_capture = int(ratio_fps)
        self.prob_extra_frame = ratio_fps - int(ratio_fps)

        self._send_fps = int(send_fps)
        self.client_app.video_client.app.setPollTime(int(1000 // send_fps))

        self.client_app.video_client.update_status_bar(self._resolution, self._send_fps)

    def set_image_resolution(self, resolution="MEDIUM"):
        self._resolution = resolution
        self.client_app.video_client.setImageResolution(resolution)
        self.client_app.video_client.update_status_bar(self._resolution, self._send_fps)

    def end_call(self, send_end_call=True, message=None):
        '''termina la llamada'''
        
        if not self.in_call():
            return

        self.set_in_call(False)
        self.client_app.end_call_window()

        if message: 
            self.client_app.video_client.app.infoBox("Info", message)

        if send_end_call:
            self.send_control_msg(
                f"CALL_END {self.client_app.ds_client.nick}"
            )
        
        self.receive_video_thread.end()
        self.receive_video_thread = None

        self.receive_control_commands_thread.end()
        self.receive_control_commands_thread = None

        self.send_data_socket.close()
        self.send_data_socket = None
        self.set_peer(None)
        
    def hold_and_resume_call(self):
        '''para o continua la llamada'''
        if self._pause and self._can_i_resume: #resume call 
            self._pause = False
            self._can_i_resume = False
            self.client_app.video_client.app.setButton("pause/resume","Pause")
            self.send_control_msg(f"CALL_RESUME {self.client_app.ds_client.nick}")
            #Cuando se pausa el video, vaciar el buffer
            self.call_buffer.empty()
            
        elif not self._pause: #pause call
            self._pause = True
            self._can_i_resume = True
            self.client_app.video_client.app.setButton("pause/resume","Resume")
            self.send_control_msg(f"CALL_HOLD {self.client_app.ds_client.nick}")

    def configure_send_socket(self):
        self.send_data_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

    def quit(self):
        if self.in_call():
            self.end_call()

    def send_control_msg(self, msg:str):
        '''envía mensaje de control'''
        try:
            TCP.send(msg, self.receive_control_commands_thread.control_socket)
        except P3Exception:
            pass

    # funciones de recepción de mensajes
    def receive_call(self, ipaddr, sock, nick, udp_port):
        '''Recibo llamada de un usuario'''
        if self.in_call():
            TCP.send("CALL_BUSY", sock)
            sock.close()
            return 

        nick, nickaddr, tcp_port, protocol = self.client_app.ds_client.query(nick)
        
        if nickaddr != ipaddr:pass
            # return -- está comentado porque dependiendo del ordenador esta comprobación puede fallar aunque el usuario sea honesto

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
            return 

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
    
    def receive_call_accepted(self, sock, udp_port):
        '''Me han aceptado llamada'''
        if self.in_call(): # para evitar errores
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
            return 
        self.end_call(False)
        self.client_app.video_client.app.infoBox("Info", f"{nick} ha colgado.")

    def receive_call_hold(self, nick):
        if not self.in_call():
            return 
        
        if not self._pause:
            self._can_i_resume = False
            self._pause = True
            
            self.client_app.video_client.app.infoBox(
                "Info", 
                f"{nick} ha puesto la llamada en hold.", 
                parent="CallWindow"
            )

    def receive_call_resume(self, nick):
        if not self.in_call():
            return 
        # solo puedo continuar si me ha pausado mi peer
        if self._pause and not self._can_i_resume:
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
    
    # manejo de intercambio de mensajes con el peer por tcp
    def make_call(self, msg, ip, tcp_port,timeout=20):
        ''' Llama a un usuario y gestiona la llamada.
            msg="CALLING nick udpport", 
            ip= la ip del usuario
            tcp_port= el puerto de control del usuario al que se llama
        '''
        try:
            control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            control_sock.settimeout(timeout) # 20 segundos esperando llamada, no más
            
            control_sock.connect((ip, tcp_port))            
            TCP.send(msg, control_sock)
            answer_msg = control_sock.recv(1 << 14).decode(encoding="utf-8")

            self.process_response_message(answer_msg, control_sock)  

        except socket.timeout:
            raise P3Exception("El usuario no ha respondido a la llamada.")
        except socket.error:
            raise P3Exception("No se pudo contactar con el usuario.")

    def process_listener_message(self, petition, connection_socket=None, addr=None):
        '''procesa una posible llamada'''
        try: 
            msg, nick, udp_port = petition.split(' ')

            if msg == "CALLING":
                self.receive_call(addr, connection_socket, nick, udp_port)

        except ValueError:
            pass # ignoramos si el listener recibe otra cosa

    def process_response_message(self, petition, connection_socket=None):
        '''procesa un mensaje que responde a CALLING...'''
        petition_list = petition.split(' ')
        try: 
            msg, nick, udp_port = petition_list
            if msg == "CALL_ACCEPTED":
                self.receive_call_accepted(connection_socket, udp_port)
        except ValueError:
            try:
                msg, nick = petition_list
                if msg == "CALL_DENIED":
                    self.receive_call_denied(nick, connection_socket)
            except ValueError:
                msg = petition_list[0]
                if msg == "CALL_BUSY":
                    self.receive_call_busy(connection_socket)

    def process_control_message(self, petition):
        '''procesa un mensaje de control durante una llamada'''
        petition_list = petition.split(' ')
        try:
            msg, nick = petition_list
            if msg == "CALL_END":
                self.receive_call_end(nick)
            elif msg == "CALL_HOLD":
                self.receive_call_hold(nick)
            elif msg == "CALL_RESUME":
                self.receive_call_resume(nick)
        except ValueError:
            pass


class ReceiveVideoThread(TerminatableThread):
    '''Hilo que recibe y reproduce los frames de una llamada'''
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
        resolution = b'0x0'
        cummulative_time = 0
        while not self.stopped():
            try:
                self.server_sock.settimeout(1/self.fps)
                data, client_address = self.server_sock.recvfrom(1 << 20)

                order_number,timestamp,resolution,fps,compressed_frame = self.split_data(data)

                self.insert_in_buffer(compressed_frame, int(order_number), float(timestamp), resolution, fps)
                cummulative_time = 0
            except (socket.timeout, ValueError):
                if self.client_app.call_manager._pause:
                    cummulative_time = 0
                else:
                    cummulative_time += 1/self.fps
              

            if cummulative_time > 5:
                self.call_manager.end_call(True, message="Se ha cortado la llamada por fallos en la conexión.")
                self.quit()
                return 

            if pause: 
                # esperar a que se llene el buffer un poco para evitar cortes por jitter
                if self.call_buffer.len < self.fps / 2:
                    pause = False 
                else:
                    continue

            while self.call_buffer.len > (self.fps) > 0:
                # tenemos más de un segundo para reproducir, podemos desechar frames 
                self.call_buffer.pop()

            try:
                self.call_manager._last_frame_shown, fts, resolution, fps, frame = self.call_buffer.pop()


                self.client_app.video_client.app.setImageData("inc_video", frame, fmt='PhotoImage')

                if self.fps != fps: 
                    self.set_receive_fps(fps)
    
            except (TypeError):
                #buffer vacio
                pause = True
                pass
        
            finally:    
                self.client_app.video_client.app.setLabel(
                    "CallInfo", 
                    f"Recibiendo datos a {self.fps} fps; resolución: {resolution.decode()}.\n"
                    +f"Tiempo de llamada: {timedelta(seconds=round(time.time()-self.call_manager.init_call_time))}")


        self.quit()

    def set_receive_fps(self, fps):
        self.fps = fps
        self.call_buffer.set_maxsize(int(fps//2)) # 0.5 segundos de vídeo en el buffer
    
    def split_data(self,data):
        '''Devuelve una lista con los elementos de la cabecera y los datos del video'''
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
        '''Inserta en el buffer una tupla (n_orden,frame descompriido) mientras no sea un frame antiguo'''
        if order_number > self.client_app.call_manager._last_frame_shown:
            decimg = cv2.imdecode(np.frombuffer(compressed_frame,np.uint8), 1)
            try:
                width, height = resolution.decode('utf-8').split('x')
                width, height = WIDTH, int(WIDTH*int(height)/int(width))
                self.client_app.video_client.app.setImageSize("inc_video",width, height)
                decimg = cv2.resize(decimg,(width,height))
            except:
                pass # por si la resolución que nos mandan no es correcta
            cv2_im = cv2.cvtColor(decimg,cv2.COLOR_BGR2RGB)
            img_tk = ImageTk.PhotoImage(Image.fromarray(cv2_im))
            self.client_app.call_manager.call_buffer.push((order_number, float(timestamp), resolution, int(fps), img_tk))
      
    def quit(self):
        self.server_sock.close()

class ReceiveControlCommandsThread(TerminatableThread):
    '''Hilo que recibe los comandos de control durante la llamada.'''
    def __init__(self, control_socket:socket.socket, call_manager: CallManager):
        super().__init__()
        self.control_socket = control_socket
        self.call_manager = call_manager

    def run(self):
        self.control_socket.settimeout(0.5)
        while not self.stopped():
            try:
                msg = self.control_socket.recv(1 << 14).decode(encoding="utf-8")
                if len(msg) > 0:
                    self.call_manager.process_control_message(msg)
            except socket.timeout:
                pass
        self.quit()

    def quit(self):
        self.control_socket.close()
