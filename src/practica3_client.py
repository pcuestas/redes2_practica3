# import the library
from appJar import gui
from PIL import Image, ImageTk
from call_manager import CallManager
import cv2
import os 
import re 

import listener
from ds_client import DSClient, DSException
from exceptions import P3Exception
from call_manager import User
from util import *


class ClientApplication(object):
    '''Clase singleton: se utiliza llamando a self.client_app'''
    _instance = None

    def __new__(self):
        if not self._instance:
            print('Creating')
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

            #Para que se cierre la app
            self.listener_thread.setDaemon(True)
            self.call_manager = CallManager(self._instance)

        return self._instance

    def start(self):
        # quitar estas líneas:
        self.ds_client.nick = 'pablo'
        self.ds_client.password = 'abcd'

        # pedir al usuario puertos y nick/password
        if not self.request_ports() or not self.request_nick_password_and_register():
            self.video_client.app.infoBox("Info", "Cerrando aplicación")
            return 

        # pregunta si quiere webcam
        capture_flag = self.video_client.app.yesNoBox("WebCam", "¿Usar cámara?")
        
        #Inicia el hilo que escucha peticiones
        self.listener_thread.start()

        # iniciar el VideoClient - la ejecución se queda 
        # aquí hasta que se salga del video client
        self.video_client.app.setLabel("title",f"{self.ds_client.nick} - Cliente Multimedia P2P ")
        self.video_client.start(capture_flag)
    
    def request_ports(self):
        while True:
            tcpp = self.request_to_user("Introduce el puerto tcp")
            if not tcpp: return False
            tcpp = int(tcpp)
            if not valid_port(tcpp):
                self.video_client.app.infoBox("Cuidado", "El puerto debe ser mayor que 1024")
            else:
                break
        
        while True:
            udpp = self.request_to_user("Introduce el puerto udp") 
            if not udpp: return False
            udpp = int(udpp)
            if not valid_port(udpp):
                self.video_client.app.infoBox("Cuidado", "El puerto debe ser mayor que 1024 y menor que 655364")
            else:
                break
            
        self._tcp_port = tcpp 
        self._udp_port = udpp
        
        # puertos leídos correctamente
        return True

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
        # correctly registered
        return True

    def request_to_user(self, msg):
        '''pide un valor al usuario en forma de texto, 
        devuelve None en caso de que el usuario no introduzca nada'''
        val = self.video_client.app.textBox(
            "ApplicationClient", msg)
        if not val:
            return None
        return val

    def request_nick_password(self):
        nick = self.request_to_user("Introduce tu nick de sesión")
        if not nick:
            return False

        password = self.request_to_user("Introduce tu contraseña")
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
        self.call_manager.quit()

    def init_call_window(self):
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
        
        if not nick: return
        
        nick, ipaddr, tcp_port, protocol = self.ds_client.query(nick)

        if self.video_client.app.yesNoBox("Llamar", f"Usuario encontrado, ¿quieres llamar a {nick}?"):
            user = User(nick, ipaddr, None, int(tcp_port))
            self.call_manager.call(user)
    
    def register_with_new_user(self):
        if self.video_client.app.questionBox(
            title="Registrar nuevo usuario",
            message=f"¿Cerrar sesión con el usuario actual: {self.ds_client.nick}?"
        ):
            if not self.request_nick_password_and_register():
                self.video_client.app.infoBox("Info", "Cerrando aplicación, es necesario tener un usuario registrado")
                self.client_app.quit()
            
    def list_of_users(self):
        users = self.ds_client.list_users()
        print("número de usuarios leídos:",len(users))
        self.video_client.display_users_list(users) #########################################################

    


class VideoClient(object):

    def __init__(self, client_application, window_size="640x720"):
        self.client_app = client_application

        # Creamos una variable que contenga el GUI principal
        self.app = gui("Redes2 - P2P", window_size)
        self.app.setGuiPadding(10,10)

        # Preparación del interfaz
        self.app.addLabel("title", "Cliente Multimedia P2P - Redes2 ")
        self.app.addImage("video", self.client_app.file("/imgs/webcam.gif"))
        self.app.setImageSize("video", 640, 640)

        self.cap = None

    def configure_call_window(self):
        self.app.startSubWindow("CallWindow", modal=True)
        self.app.addLabel("msg_call_window", f" {self.client_app.ds_client.nick}-Ventana de llamada")
        self.app.addImage("inc_video",self.client_app.file("/imgs/webcam.gif"))
        self.app.setImageSize("inc_video",800,600)
        self.app.addButtons(["Colgar llamada"],self.buttonsCallback)
        self.app.addStatusbar(fields=2)

        self.app.stopSubWindow()

    def configure_list_users_window(self):
        self.app.startSubWindow("ListUsers", modal=True)
        self.app.addTable("ListUsersTable",[[1]])
        self.app.addButtons(["Cerrar"], self.buttonsCallbackListUsers)
        self.app.stopSubWindow()

    def update_status_bar(self,resolution,fps):
        self.app.setStatusbar(f"Enviando a resolucion {resolution}", 0)
        self.app.setStatusbar(f"FPS: {fps} ", 1)
                    
    # Función que gestiona los callbacks de los botones
    def buttonsCallback(self, button):
        try:
            if button == "Salir":
                # Salimos de la aplicación
                self.client_app.quit()

            elif button == "Conectar":
                self.client_app.connect()

            elif button == "Registrar con otro usuario":
                self.client_app.register_as_new_user()
            
            elif button == "Lista de usuarios":
                self.client_app.list_of_users()

            elif button =="Colgar llamada":
                self.client_app.call_manager.end_call()
        except P3Exception as e:
            self.app.infoBox("Error", e)

    def buttonsCallbackListUsers(self, button):
        try: 
            if button == "Cerrar":
                self.app.hideSubWindow("ListUsers")
        except P3Exception as e:
            self.app.infoBox("Error", e)

    def start(self, capture_flag):
        self.config_capture_video(capture_flag)
        self.app.go()

    def config_capture_video(self, capture_flag):
        # Registramos la función de captura de video
        # Esta misma función también sirve para enviar un vídeo
        
        if capture_flag:
            print("Voy a usar camara")
            self.cap = cv2.VideoCapture(0)
        else:
            print("Voy a usar video")
            self.cap = cv2.VideoCapture(self.client_app.file("/imgs/webcam.gif"))
            
        self.app.setPollTime(20)
        self.app.registerEvent(self.capturaVideo)

        # Añadir los botones
        self.app.addButtons(
            ["Conectar", "Lista de usuarios", "Registrar con otro usuario", "Salir"], 
            self.buttonsCallback
        )        

        self.configure_call_window()
        self.configure_list_users_window()
        # Barra de estado
        # Debe actualizarse con información útil sobre la llamada (duración, FPS, etc...)
     
    # Función que captura el frame a mostrar en cada momento
    def capturaVideo(self):
        
        # Capturamos un frame de la cámara o del vídeo
        ret, frame = self.cap.read()
        
        frame = cv2.resize(frame, (640, 480))
        cv2_im = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_tk = ImageTk.PhotoImage(Image.fromarray(cv2_im))

        # Lo mostramos en el GUI
        self.app.setImageData("video", img_tk, fmt='PhotoImage')

        # Aquí tendría que el código que envia el frame a la red
        if self.client_app.call_manager.in_call():
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, 50]
            result, encimg = cv2.imencode('.jpg', frame, encode_param)
            if not result:
                print('Error al codificar imagen')
            self.client_app.call_manager.send_datagram(encimg.tobytes())

    # Establece la resolución de la imagen capturada
    def setImageResolution(self, resolution):        
        # Se establece la resolución de captura de la webcam
        # Puede añadirse algún valor superior si la cámara lo permite
        # pero no modificar estos
        if resolution == "LOW":
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 160) 
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 120) 
        elif resolution == "MEDIUM":
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320) 
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240) 
        elif resolution == "HIGH":
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640) 
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) 

    def display_users_list(self, users):
        self.app.replaceAllTableRows(
            "ListUsersTable",
            [["Nick", "IP", "TCP port"]] + users
        )
        self.app.showSubWindow("ListUsers")
        

    def stop(self):
        self.app.stop()

if __name__ == '__main__':

    # Inicialización de la aplicación
    app = ClientApplication()

    # Lanza el bucle principal del aplicación
    # El control ya NO vuelve de esta función, por lo que todas las
    # acciones deberán ser gestionadas desde callbacks y threads
    app.start()