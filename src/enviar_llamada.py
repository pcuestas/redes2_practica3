import socket
import time

import cv2



def capturar_video():
    ret, img = cap.read() # lectura de un frame de vídeo

    # Compresión JPG al 50% de resolución (se puede variar)
    encode_param = [cv2.IMWRITE_JPEG_QUALITY,50]
    result,encimg = cv2.imencode('.jpg',img,encode_param)
    if result == False: print('Error al codificar imagen')
    return encimg.tobytes()

serverName = '127.0.1.1'
serverPort = 11001
puerto_UDP= 11000
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect((serverName,serverPort))
sentence = "CALLING zama 1234"
clientSocket.send(sentence.encode())
modifiedSentence = clientSocket.recv(1024)
print('Desde␣el␣servidor:', modifiedSentence)
clientSocket.close()


cap = cv2.VideoCapture(0)


socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
i=0
while i<1000:
    message="{}".format(i).encode()
    
    video = capturar_video()
    sent = socket.sendto(video,(serverName,puerto_UDP))
    print(f"vid:{len(video)}. sent:{sent}")
    time.sleep(1)
    #print("Envio {}".format(i))
    i+=1


#terminar llamada
#message="CALL_END zama".encode()
#socket.sendto(message,(serverName,puerto_UDP))