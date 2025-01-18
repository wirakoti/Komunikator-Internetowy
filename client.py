import socket
import tkinter as tk
from tkinter import scrolledtext
import threading

from duplicity.asyncscheduler import thread
from pydantic.dataclasses import dataclass

HOST = "127.0.0.1"
PORT = 1100  

class SocketClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Socket Client")

        # chat
        self.chat_display = scrolledtext.ScrolledText(self.root, height=20, width=50, wrap=tk.WORD)
        self.chat_display.pack(padx=10, pady=10)
        self.chat_display.config(state=tk.DISABLED)

        # message entry
        self.entry_field = tk.Entry(self.root, width=40)
        self.entry_field.pack(padx=10, pady=10)
        self.entry_field.bind("<Return>", self.send_message)
        self.entry_field.config(state=tk.DISABLED)
        
        self.connect_button = tk.Button(self.root, text="Connect", command=self.connect_to_server)
        self.connect_button.pack(pady=5)

        self.register_button = tk.Button(self.root, text="Register", command=self.register_user)
        self.register_button.pack(pady=5)

        self.login_button = tk.Button(self.root, text="Login", command=self.login_user)
        self.login_button.pack(pady=5)

        self.exit_button = tk.Button(self.root, text="Exit", command=self.exit_app)
        self.exit_button.pack(pady=5)

        # login + password
        self.login_field = tk.Entry(self.root, width=40)
        self.login_field.pack(padx=10, pady=5)
        self.login_field.insert(0, "Enter Username")

        self.password_field = tk.Entry(self.root, width=40, show="*")
        self.password_field.pack(padx=10, pady=5)
        self.password_field.insert(0, "xxxxxxxxxx")

        self.socket = None
        self.logged_in = False  

    def connect_to_server(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((HOST, PORT))
            self.append_to_chat("connected to server at {}:{}".format(HOST, PORT))

            threading.Thread(target=self.receive_message, daemon=True).start()
        except Exception as e:
            self.append_to_chat("error connecting to server: " + str(e))

    def register_user(self):
        login = self.login_field.get().strip()
        password = self.password_field.get().strip()

        if login and password:
            message = f"REGISTER {login} {password}"
            self.socket.send(message.encode('utf-8'))
            data = self.socket.recv(1024)
            self.append_to_chat(f"[server]: {data.decode('utf-8')}")
        else:
            self.append_to_chat("Please enter a username and password.")

    def login_user(self):
        login = self.login_field.get().strip()
        password = self.password_field.get().strip()

        if login and password:
            message = f"LOGIN {login} {password}"
            self.socket.send(message.encode('utf-8'))
            data = self.socket.recv(1024)
            response = data.decode('utf-8')
            self.append_to_chat(f"[server]: {response}")

            if "successful" in response:
                self.logged_in = True
                self.toggle_login_register_controls(False)  
                self.entry_field.config(state=tk.NORMAL)  
        else:
            self.append_to_chat("Please enter a username and password.")

    def send_message(self, event=None):
        msg = self.entry_field.get().strip()
        if msg == "exit":
            self.append_to_chat("exited!")
            if self.socket:
                self.socket.close()
            self.root.quit()
            return
        if self.socket and self.logged_in:
            try:
                self.socket.send(bytes(msg, "utf-8"))
                # data = self.socket.recv(1024)
                # self.append_to_chat("[you]: " + msg)
                # self.append_to_chat("[server]: " + data.decode("utf-8"))
            except Exception as e:
                self.append_to_chat("error: " + str(e))
        else:
            self.append_to_chat("you need to log in before sending messages!")

        self.entry_field.delete(0, tk.END)

    def receive_message(self):
        while True:
            try:
                data = self.socket.recv(1024).decode("utf-8")
                if data:
                    self.root.after(0, self.append_to_chat(data))
            except Exception as e:
                self.append_to_chat("error: " + str(e))
                break

    def toggle_login_register_controls(self, enable):
        if enable:
            self.register_button.pack(pady=5)
            self.login_button.pack(pady=5)
        else:
            self.register_button.pack_forget()
            self.login_button.pack_forget()

    def append_to_chat(self, text):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, text + "\n")
        self.chat_display.yview(tk.END)  # scroll
        self.chat_display.config(state=tk.DISABLED)

    def exit_app(self):
        self.append_to_chat("Connection closed!")
        if self.socket:
            self.socket.close()
        self.root.quit()

def run_app():
    root = tk.Tk()
    app = SocketClientApp(root)
    root.mainloop()

if __name__ == "__main__":
    run_app()
