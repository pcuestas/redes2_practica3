

from appJar import gui
from PIL import Image, ImageTk
from call_manager import CallManager
import cv2
import os 
import re
import numpy as np
import os
from PIL import ImageGrab
import random

import listener
from ds_client import DSClient, DSException
from exceptions import P3Exception
from call_manager import User
from util import *

MAX_FPS = 60
MIN_FPS = 10
CAM_SIZE = (640, 480)

class ClientApplication(object):
    '''Clase singleton: se utiliza llamando a self.client_app'''
    _instance = None
    _initial_register = False

    def __new__(self):
        if not self._instance:
            self._instance = super(
                ClientApplication, self).__new__(self)

            # quitar ?
            self._udp_port = 11000
            self._tcp_port = 11001

            
            # directorio de los ficheros de la aplicación
            self.APPFILES_DIR = re.sub(
                '/\w*/\.\.', '', os.path.dirname(__file__) + '/../appfiles')

            self.video_client = VideoClient(self._instance)

            # Crear aquí los threads de lectura, de recepción y,
            # en general, todo el código de inicialización que sea necesario
            # ...
            self.ds_client = DSClient(self._instance)
            self.listener_thread = listener.ListenerThread(
                self._instance,
                self.video_client
            )

            self.call_manager = CallManager(self._instance)

        return self._instance

    def start(self):
        self.video_client.request_initial_register()
        self.video_client.start()

    def start_after_register(self):

        #Inicia el hilo que escucha peticiones
        self.listener_thread.setDaemon(True)
        self.listener_thread.start()

        self.video_client.app.setLabel("title",f"{self.ds_client.nick} - Cliente Multimedia P2P ")

        # iniciar el VideoClient - la ejecución se queda 
        # aquí hasta que se salga del video client
        self.video_client.start_after_register()

    def initial_register_button(self, button):
        if button == "Cerrar" or ClientApplication()._initial_register:
            self.video_client.stop()
            return 

        entries = self.video_client.app.getAllEntries()
        try:
            tcpp,udpp, = int(entries["tcpp"]),int(entries["udpp"])
            nick,passw = entries["nick"], entries["pass"]
        except:
            self.video_client.app.infoBox("Error","Se deben rellenar todos los campos.")
            return 
        
        if not valid_port(tcpp) or not valid_port(udpp):
            self.video_client.app.infoBox("Cuidado", "El puerto debe ser mayor que 1024 y menor que 655364.")
            return 
        
        self._tcp_port = tcpp
        self._udp_port = udpp

        try:
            self.ds_client.nick = nick 
            self.ds_client.password = passw
            self.ds_client.register()
            self.video_client.app.hideSubWindow("Register")
            ClientApplication()._initial_register = True
        except DSException as e:
            self.video_client.app.infoBox("Error.", str(e))
            return 

        # lanzar la aplicación 
        self.start_after_register()

    def request_nick_password_and_register(self):
        while True:
            if not self.request_nick_password():
                # user closes the nick/password window
                return False
            try:
                # registrar usuario
                self.ds_client.register()
                break
            except DSException as e:
                self.video_client.app.infoBox("Error", str(e))
        # registrado correctamente
        return True

    def request_nick_password(self):
        nick = self.video_client.app.textBox(
            "ApplicationClient", "Introduce tu nick de sesión")
        if not nick:
            return False

        password = self.video_client.app.textBox(
            "ApplicationClient", "Introduce tu contraseña")
        if not password:
            return False

        self.ds_client.nick = nick 
        self.ds_client.password = password

        return True

    def quit(self):
        print("Cerrando aplicación.")

        self.video_client.stop()
        # mandar quit al servidor
        self.ds_client.quit()

        # cerrar aquí todos los hilos...
        self.listener_thread.end()
        self.call_manager.quit()

    def init_call_window(self):
        self.video_client.app.setButton("pause/resume","Pause")
        self.video_client.app.showSubWindow("CallWindow")

    def end_call_window(self):
        self.video_client.app.hideSubWindow("CallWindow")

    def file(self, location):
        '''toma un path relativo al directorio de los ficheros de la 
           aplicación de la forma: "/imgs/file.png" y devuelve el path completo'''
        return self.APPFILES_DIR + location

    def connect(self):
        # Entrada del nick del usuario a conectar    
        nick = self.video_client.app.textBox("Conexión", 
            "Introduce el nick del usuario a buscar")
        
        if not nick: 
            return
        if nick == self.ds_client.nick:
            self.video_client.app.infoBox(
                "Info",
                f"Tú mismo eres el usuario {nick} (no te puedes llamar a tí mismo)."
            )
            return 
        
        nick, ipaddr, tcp_port, protocol = self.ds_client.query(nick)

        if self.video_client.app.yesNoBox("Llamar", f"Usuario encontrado, ¿quieres llamar a {nick}?"):
            user = User(nick, ipaddr, None, int(tcp_port))
            self.call_manager.call(user)
    
    def register_as_new_user(self):
        if self.video_client.app.questionBox(
            title="Registrar nuevo usuario",
            message=f"¿Cerrar sesión con el usuario actual: {self.ds_client.nick}?"
        ):
            if not self.request_nick_password_and_register():
                self.video_client.app.infoBox("Info", "Cerrando aplicación, es necesario tener un usuario registrado")
                self.client_app.quit()
            
            #actualizar el nombre en la ventana
            self.video_client.app.setLabel("title",f"{self.ds_client.nick} - Cliente Multimedia P2P ")
            
    def list_of_users(self):
        users = self.ds_client.list_users()
        self.video_client.display_users_list(users) 



class VideoClient(object):

    def __init__(self, client_application, window_size="720x720"):
        self.client_app = client_application

        # Creamos una variable que contenga el GUI principal
        self.app = gui("Redes2 - P2P", window_size)
        self.app.setGuiPadding(10,10)

        # Preparación del interfaz
        self.app.addLabel("title", "Cliente Multimedia P2P - Redes2 ")
        self.app.addImage("video", self.client_app.file("/media/webcam.gif"))
        self.app.setImageSize("video", CAM_SIZE[0], CAM_SIZE[1])
        self.app.setLocation(x=0, y=0)

        self.cap = None
        self.screen_cap = False 
        self.resource_fps = 20
        self.CAM_SIZE = (640,480)
        self.using_webcam = False

    def configure_call_window(self):
        self.app.startSubWindow("CallWindow", modal=True)
        self.app.setStopFunction(self.client_app.call_manager.end_call)

        self.app.setSize(self.CAM_SIZE[0]+100, self.CAM_SIZE[1]+200)
        
        self.app.addLabel("msg_call_window", f" {self.client_app.ds_client.nick}-Ventana de llamada")
        self.app.addLabel("CallInfo", "")
        self.app.addImage("inc_video", self.client_app.file("/media/webcam.gif"))
        self.app.setImageSize("inc_video", self.CAM_SIZE[0], self.CAM_SIZE[1])


        #START TAB PANE
        self.app.startTabbedFrame("TabLlamada")

        self.app.startTab("Acciones")
        self.app.addButtons(["Colgar"], self.buttonsCallback)
        self.app.addNamedButton("Pausar", "pause/resume", self.buttonsCallback)
        self.app.stopTab()

        self.app.startTab("Ajustar resolución de envío")
        self.app.addRadioButton("resolution","LOW")
        self.app.addRadioButton("resolution","MEDIUM")
        self.app.addRadioButton("resolution","HIGH")
        self.app.addButton("Cambiar resolución", self.buttonsCallback)
        self.app.stopTab()

        self.app.startTab("Cambiar FPS")
        self.app.addLabel("FPS a enviar")
        self.app.addNumericEntry("input_fps")
        self.app.addButtons(["Cambiar fps"], self.buttonsCallback)
        self.app.stopTab()

        self.app.startTab("Recurso a enviar")
        self.app.addLabel("c","Select webcam or video to send")

        fileslist = os.listdir(self.client_app.file("/media"))

        self.app.addOptionBox("optionbox", ["Webcam", "Capture screen"] + fileslist)
        self.app.setOptionBoxChangeFunction("optionbox", self.select_media_resource)
        self.app.stopTab()
        self.app.addStatusbar(fields=2)

        self.app.stopTabbedFrame()
        #END TAB PANE

        self.app.stopSubWindow()

    def configure_list_users_window(self):
        self.app.startSubWindow("ListUsers", modal=True)
        self.app.setSize(640, 700)

        self.app.addListBox("ListBoxUsers",values=[])
        self.app.setListBoxWidth("ListBoxUsers", 60)
        self.app.setListBoxHeight("ListBoxUsers", 30)

        self.app.addButtons(["Cerrar lista"], self.buttonsCallbackListUsers)
        self.app.stopSubWindow()

    def request_initial_register(self):
        self.app.startSubWindow("Register", modal=True)

        self.app.setStopFunction(self.stop)

        self.app.addLabel("lr1", "Puerto TCP:")
        self.app.addEntry("tcpp")
        self.app.setEntry("tcpp", str(np.random.randint(4000, 11000)))

        self.app.addLabel("lr2", "Puerto UDP:")
        self.app.addEntry("udpp")
        self.app.setEntry("udpp", str(np.random.randint(4000, 11000)))

        self.app.addLabel("lr3", "Nick:")
        self.app.addEntry("nick")

        self.app.addLabel("lr4", "Contraseña:")
        self.app.addSecretEntry("pass")

        self.app.addButtons(["Entrar", "Cerrar"], self.client_app.initial_register_button)
        self.app.stopSubWindow()
        
        self.app.showSubWindow("Register")

    def select_media_resource(self):
        opt=self.app.getOptionBox("optionbox")
        if opt == "Webcam":
            self.set_video_capture(use_webcam=True)
        elif opt == "Capture screen":
            self.set_video_capture(use_webcam=False,screen_cap=True)
        else:
            self.set_video_capture(use_webcam=False, resource_name=opt)

    def update_status_bar(self, resolution, fps):
        self.app.setStatusbar(f"Enviando a resolución {resolution}", 0)
        self.app.setStatusbar(f"Enviando a {fps} fps", 1)
                    
    # Función que gestiona los callbacks de los botones
    def buttonsCallback(self, button):
        try:
            if button == "Salir":
                self.client_app.quit()

            elif button == "Conectar":
                self.client_app.connect()

            elif button == "Registrar con otro usuario":
                self.client_app.register_as_new_user()
            
            elif button == "Lista de usuarios":
                self.client_app.list_of_users()

            elif button == "Colgar":
                self.client_app.call_manager.end_call()

            elif button == "pause/resume":
                self.client_app.call_manager.hold_and_resume_call()

            elif button == "Cambiar resolución":
                resolution=self.app.getRadioButton("resolution")
                self.client_app.call_manager.set_image_resolution(resolution)
            
            elif button == "Cambiar fps":
                fps=int(self.app.getEntry("input_fps"))
                self.client_app.call_manager.set_send_fps(fps)
            
        except P3Exception as e:
            self.app.infoBox("Error", e)

    def buttonsCallbackListUsers(self, button):
        try: 
            if button == "Cerrar lista":
                self.app.hideSubWindow("ListUsers")
        except P3Exception as e:
            self.app.infoBox("Error", e)

    def start(self):
        self.app.go()

    def start_after_register(self):
        self.config_capture_video_settings()

    def config_capture_video_settings(self):
        # Registramos la función de captura de video        
        self.set_video_capture(use_webcam=False,resource_name="home_page.gif")
            
        self.app.registerEvent(self.capturaVideo)

        # Añadir los botones
        self.app.addButtons(
            ["Conectar", "Lista de usuarios", "Registrar con otro usuario", "Salir"], 
            self.buttonsCallback
        )        

        self.configure_call_window()
        self.configure_list_users_window()
     
    def set_video_capture(self, use_webcam: bool = True, resource_name="videoplayback.mp4", screen_cap=False):

        if screen_cap:
            self.screen_cap = True 
            return 

        file_name = "/media/"+resource_name
        err = False
        self.screen_cap = False 
        self.using_webcam = False
        try:
            if use_webcam:
                self.cap = cv2.VideoCapture(0)
                self.using_webcam = True
                if not self.cap.isOpened():
                    err = True
                    print("No se pudo abrir la webcam, utilizando vídeo por defecto.")
                    self.using_webcam = False
                self.resource_fps = 25

            else:
                self.cap = cv2.VideoCapture(self.client_app.file(file_name)) 
                self.resource_fps = self.cap.get(cv2.CAP_PROP_FPS)
                if not self.resource_fps:
                    err = True
        except:
            err = True
            print("Hubo algún error, utilizando vídeo por defecto.")

        if err:
            self.cap = cv2.VideoCapture(self.client_app.file("/media/videoplayback.mp4"))
            self.resource_fps = self.cap.get(cv2.CAP_PROP_FPS)
             
        self.resource_fps = min(max(self.resource_fps,MIN_FPS), MAX_FPS)
        self.client_app.call_manager.set_send_fps(fps=self.resource_fps)
     
    # Función que captura el frame a mostrar en cada momento
    def capturaVideo(self):
        try:
            if self.screen_cap:
                img = ImageGrab.grab() 
                frame = np.array(img)
                frame = cv2.resize(frame, CAM_SIZE)
                cv2_im = frame # para mostrar por pantalla
                frame_send = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) # para enviar
            else:
                # Capturamos tantos frames como sea necesario para igualar los fps de envio con los fps del recurso
                if not self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

                ret = None
                for _ in range(self.client_app.call_manager.frames_per_capture):
                    ret, frame_send = self.cap.read()
                if random.random() < self.client_app.call_manager.prob_extra_frame:
                    ret, frame_send = self.cap.read()

                if not ret:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    return 
                frame = cv2.resize(frame_send, CAM_SIZE)
                cv2_im = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            img_tk = ImageTk.PhotoImage(Image.fromarray(cv2_im))

            # Lo mostramos en el GUI
            self.app.setImageData("video", img_tk, fmt='PhotoImage')

            # Aquí tendría que el código que envia el frame a la red
            if self.client_app.call_manager.in_call():
                encode_param = [cv2.IMWRITE_JPEG_QUALITY, 50]
                ret, encimg = cv2.imencode('.jpg', frame_send, encode_param)
                if ret:
                    self.client_app.call_manager.send_datagram(encimg.tobytes())
        except cv2.error as e:
            pass

    # Establece la resolución de la imagen capturada
    def setImageResolution(self, resolution):        
        # Se establece la resolución de captura de la webcam
        # Puede añadirse algún valor superior si la cámara lo permite
        # pero no modificar estos
        if resolution == "LOW":
            self.CAM_SIZE = (160,120)
        elif resolution == "MEDIUM":
            self.CAM_SIZE = (320,240)
        elif resolution == "HIGH":
            self.CAM_SIZE = (640,480)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.CAM_SIZE[0]) 
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.CAM_SIZE[1]) 

    def display_users_list(self, users):
        self.app.clearListBox("ListBoxUsers")
        listusers = []
        for i,s in enumerate(users):
            try:
                listusers+=[f"  {i}. Nombre: '{s[0]}'; IP: {s[1]}; puerto: {s[2]}."]
            except IndexError:
                pass
        self.app.updateListBox(
            "ListBoxUsers",
              ["        USUARIOS EN EL SERVIDOR"] + listusers
        )
        self.app.showSubWindow("ListUsers")

    def stop(self):
        self.app.stop()

if __name__ == '__main__':
    
    # crear el fichero de media
    MEDIA_DIR = os.path.dirname(__file__) + '/../appfiles/media'
    if not os.path.exists(MEDIA_DIR):
        os.makedirs(MEDIA_DIR)

    # Inicialización de la aplicación
    app = ClientApplication()

    # Lanza el bucle principal del aplicación
    # El control ya NO vuelve de esta función, por lo que todas las
    # acciones deberán ser gestionadas desde callbacks y threads
    app.start()
    

