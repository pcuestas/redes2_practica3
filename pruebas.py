
import socket
from appJar import gui 


def list_users():
    server_port = 8000
    server_name = "vega.ii.uam.es"

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_name,server_port))

    client_socket.send("LIST_USERS".encode(encoding="utf-8"))
    response = client_socket.recv(1024).decode(encoding="utf-8")
    return response



print(list_users())

def process_list_users(list_user:str, app):
    '''
        Recibe N #User1....#
    '''
    index=list_user.find(' ')
    n=int(list_user[:index])
    users=list_user[index+1:]
    print("Hay {} usuarios".format(n))
    i=0

    
    app.startScrollPane("PANE")
    for user in users.split('#'):
        # nick ip port
        try:
            items=user.split(' ')
            app.addLabel("{} f".format(i), items[0], row=i, column=1)
            app.addLabel("{} g".format(i), items[1], row=i, column=2)
            app.addLabel("{} h".format(i), items[2], row=i, column=3)
            #print("User {} es : {} {} {}".format(i,items[0],items[1],items[2]))
            i+=1
        except:
            break
    app.stopScrollPane()



app=gui("SCROLLABLE DEMO", "150x150")
process_list_users(list_users()[14:],app)
app.go()
