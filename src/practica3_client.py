# import the library
from appJar import gui
from PIL import Image, ImageTk
import numpy as np
import cv2
import os
import re

from ds_client import DSClient
from exceptions import P3Exception
from listener import *

class ClientApplication(object):
    '''Clase singleton: se utiliza llamando a ClientApplication()'''
    _instance = None

    def __new__(self):
        if not ClientApplication._instance:
            print('Creating')
            ClientApplication._instance = super(ClientApplication, self).__new__(self)
            
            # directorio de los ficheros de la aplicación
            self.APPFILES_DIR = re.sub('/\w*/\.\.','', os.path.dirname(__file__) + '/../appfiles')

            self.video_client = VideoClient("640x520", self)

            # Crear aquí los threads de lectura, de recepción y,
            # en general, todo el código de inicialización que sea necesario
            # ...
            self.ds_client = DSClient(nick="pablo",password="abcd")
            self.listener_thread = ListenerThread(self.video_client)
            self.listener_thread.setDaemon(True)
        return self._instance

    #def __init__(self):

        
    
    def start(self):
        # crear usuario
        self.ds_client.register()
        # iniciar el VideoClient

        #Inicia el hilo que escucha peticiones
        self.listener_thread.start()

        self.video_client.start()


    def quit(self):
        print("Cerrando aplicación.")
        # mandar quit al servidor
        self.ds_client.quit()
    
    def query(self, nick):
        print(self.ds_client.query(nick))

    def file(self, location):
        '''toma un path relativo al directorio de los ficheros de la 
           aplicación de la forma: "/imgs/file.png" y devuelve el path completo'''
        return self.APPFILES_DIR + location  

class VideoClient(object):

    def __init__(self, window_size, client_application):
        self.client_application = client_application

        # Creamos una variable que contenga el GUI principal
        self.app = gui("Redes2 - P2P", window_size)
        self.app.setGuiPadding(10,10)

        # Preparación del interfaz
        self.app.addLabel("title", "Cliente Multimedia P2P - Redes2 ")
        self.app.addImage("video", ClientApplication().file("/imgs/webcam.gif"))

        # Registramos la función de captura de video
        # Esta misma función también sirve para enviar un vídeo
        self.cap = cv2.VideoCapture(0)
        self.app.setPollTime(20)
        self.app.registerEvent(self.capturaVideo)

        # Añadir los botones
        self.app.addButtons(["Conectar", "Colgar", "Salir"], self.buttonsCallback)
        
        # Barra de estado
        # Debe actualizarse con información útil sobre la llamada (duración, FPS, etc...)
        self.app.addStatusbar(fields=2)

    def start(self):
        self.app.go()

    # Función que captura el frame a mostrar en cada momento
    def capturaVideo(self):
        
        # Capturamos un frame de la cámara o del vídeo
        ret, frame = self.cap.read()
        frame = cv2.resize(frame, (640,480))
        cv2_im = cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
        img_tk = ImageTk.PhotoImage(Image.fromarray(cv2_im))            

        # Lo mostramos en el GUI
        self.app.setImageData("video", img_tk, fmt = 'PhotoImage')

        # Aquí tendría que el código que envia el frame a la red
        # ...

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
                
    # Función que gestiona los callbacks de los botones
    def buttonsCallback(self, button):
        try:
            if button == "Salir":
                # Salimos de la aplicación
                self.app.stop()
                ClientApplication().quit()
            elif button == "Conectar":
                # Entrada del nick del usuario a conectar    
                nick = self.app.textBox("Conexión", 
                    "Introduce el nick del usuario a buscar")
                ClientApplication().query(nick)
        except P3Exception as e:
            print(e)
  

if __name__ == '__main__':

    # Inicialización de la aplicación
    app = ClientApplication()

    # Lanza el bucle principal del aplicación
    # El control ya NO vuelve de esta función, por lo que todas las
    # acciones deberán ser gestionadas desde callbacks y threads
    app.start()