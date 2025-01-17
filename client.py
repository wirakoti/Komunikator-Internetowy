import socket

HOST="127.0.0.1"
PORT=1100

# niech klient działa w pętli
# na początku przeczytać dane z konsoli
# wysłać je i odebrać
# jeżeli input z konsoli =="exit" wyjść z pętli i zakończyć 
połączenie

with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
    s.connect((HOST,PORT))
    while True:
        msg=input()
        if msg =="exit":
            break

        s.send(bytes(msg,"utf-8"))
        data=s.recv(1024)
        print(data)

    s.close()
