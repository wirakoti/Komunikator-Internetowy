import socket
import tkinter as tk
from tkinter import scrolledtext, simpledialog, Frame
import threading

from duplicity.asyncscheduler import thread
from pydantic.dataclasses import dataclass

HOST = "127.0.0.1"
PORT = 1100  

class SocketClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Socket Client")

        # buttons for chats
        self.chat_frames = {}
        self.current_chat = None

        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(side=tk.TOP)

        self.chat_button_1 = tk.Button(self.top_frame, text="SERVER", command=lambda: self.toggle_chats("SERVER"))
        self.chat_button_1.pack(side=tk.LEFT)

        self.chat_button_2 = tk.Button(self.top_frame, text="+", command=self.create_new_chat)
        self.chat_button_2.pack(side=tk.RIGHT)
        self.chat_button_2.config(state=tk.DISABLED)

        # for chat and active users to be next to each other
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.chat_frame = tk.Frame(self.main_frame)
        self.chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


        self.active_users_frame = tk.Frame(self.main_frame)
        self.active_users_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)


        self.active_users_label = tk.Label(self.active_users_frame, text="Active Users", font=("Arial", 12, "bold"))
        self.active_users_label.pack()

        self.active_users_listbox = tk.Listbox(self.active_users_frame, width=30, height=15)
        self.active_users_listbox.pack()

        self.toggle_chats("SERVER")

        # message entry
        self.entry_field = tk.Entry(self.root, width=40)
        self.entry_field.pack(padx=10, pady=10)
        self.entry_field.bind("<Return>", self.send_message)
        self.entry_field.config(state=tk.DISABLED)
       
        self.connect_button = tk.Button(self.root, text="Connect", command=self.connect_to_server)
        self.connect_button.pack(pady=5)

        self.active_users_button = tk.Button(self.root, text="Active Users", command=self.get_active_users)
        self.active_users_button.pack(pady=5)

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

            if response.startswith("login successful:"):
                self.logged_in = True
                self.toggle_login_register_controls(False)
                self.entry_field.config(state=tk.NORMAL)
                self.chat_button_2.config(state=tk.NORMAL)
                self.login_field.pack_forget()
                self.password_field.pack_forget()

                chatrooms = response.split(":")[1].strip().split()
                for chatroom in chatrooms:
                    if chatroom not in self.chat_frames:
                        self.toggle_chats(chatroom)

                        chat_button = tk.Button(
                            self.top_frame, text=chatroom,
                            command=lambda cr=chatroom: self.toggle_chats(cr)
                        )
                        chat_button.pack(side=tk.LEFT)

                threading.Thread(target=self.receive_message, daemon=True).start()
            else:
                self.append_to_chat("Login failed. Please check your credentials.")
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
                msg = f"{self.current_chat} {msg}"
                self.socket.send(bytes(msg, "utf-8"))
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
                    if data.startswith("ACTIVE_USERS:"):
                        # for active users cause i cant......
                        active_users = data[len("ACTIVE_USERS:"):].strip()
                        self.root.after(0, lambda: self.show_active_users(active_users))
                    else:
                        # username chatname message
                        parts = data.split(maxsplit=2)
                        if len(parts) == 3:
                            sender, chat_name, message = parts
                            fmsg = f"[{sender}]: {message}"
                            self.root.after(0, lambda: self.append_to_chat(fmsg, chat_name))
                        else:
                            self.root.after(0, lambda: self.append_to_chat(f"Invalid message received: {data}"))
            except Exception as e:
                self.root.after(0, lambda: self.append_to_chat(f"Error receiving message: {str(e)}"))
                break

   
    def get_active_users(self):
        if self.socket:
            threading.Thread(target=self.fetch_active_users, daemon=True).start()
        else:
            self.append_to_chat("You are not connected to the server.")

    def fetch_active_users(self):
        try:
            self.socket.send("GET_ACTIVE_USERS".encode("utf-8"))
        except Exception as e:
            self.append_to_chat(f"Error retrieving active users: {str(e)}")

   
    def show_active_users(self, users):
        self.active_users_listbox.delete(0, tk.END)  # clearing to refresh
        active_users_list = users.split() 
        for user in active_users_list:
            self.active_users_listbox.insert(tk.END, user)

    def toggle_login_register_controls(self, enable):
        if enable:
            self.register_button.pack(pady=5)
            self.login_button.pack(pady=5)
        else:
            self.register_button.pack_forget()
            self.login_button.pack_forget()

    def toggle_chats(self, name):
        if name not in self.chat_frames:
            frame = scrolledtext.ScrolledText(self.chat_frame, height=20, width=50, wrap=tk.WORD)
            frame.pack(padx=10, pady=0)
            frame.config(state=tk.DISABLED)
            self.chat_frames[name] = frame

        self.show_chat(name)

    def show_chat(self, chat_name):
        if self.current_chat:
            self.chat_frames[self.current_chat].pack_forget()

        self.chat_frames[chat_name].pack(padx=10, pady=0)

        self.current_chat = chat_name

    def create_new_chat(self):
        chat_name = simpledialog.askstring("New chat", "Enter the name for the new chat: ")
        if chat_name:
            self.toggle_chats(chat_name)

            new_chat_button = tk.Button(self.top_frame, text=chat_name, command=lambda: self.toggle_chats(chat_name))
            new_chat_button.pack(side=tk.LEFT)

            msg = f"JOIN {chat_name}"
            self.socket.send(bytes(msg, "utf-8"))

    def append_to_chat(self, text, chat_name = "SERVER"):
        chat_display = self.chat_frames[chat_name]
        chat_display.config(state=tk.NORMAL)
        chat_display.insert(tk.END, text + "\n")
        chat_display.yview(tk.END)  # scroll
        chat_display.config(state=tk.DISABLED)

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
