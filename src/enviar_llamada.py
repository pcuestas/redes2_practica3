import socket

serverName = '127.0.1.1'
serverPort = 12000
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect((serverName,serverPort))
sentence = "CALLING zama 1234"
clientSocket.send(sentence.encode())
modifiedSentence = clientSocket.recv(1024)
print('Desde␣el␣servidor:', modifiedSentence)
clientSocket.close()