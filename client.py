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

        # for chat + friends and active users to be next to each other

        self.left_frame = tk.Frame(self.root)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.active_users_frame = tk.Frame(self.root)
        self.active_users_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        self.active_users_label = tk.Label(self.active_users_frame, text="Active Users", font=("Arial", 12, "bold"))
        self.active_users_label.pack()

        self.active_users_listbox = tk.Listbox(self.active_users_frame, width=30, height=10)
        self.active_users_listbox.pack()

        self.friends_frame = tk.Frame(self.active_users_frame)
        self.friends_frame.pack(fill=tk.Y, padx=10, pady=10)

        self.friends_label = tk.Label(self.friends_frame, text="Friends", font=("Arial", 12, "bold"))
        self.friends_label.pack()

        self.friends_listbox = tk.Listbox(self.friends_frame, width=30, height=10)
        self.friends_listbox.pack()

        # self.active_users_button = tk.Button(self.active_users_frame, text="Active Users", command=self.get_active_users)
        # self.active_users_button.pack(pady=5)
        self.button_show_friends = tk.Button(self.active_users_frame, text="Show Friends", command=self.show_friends)
        self.button_show_friends.pack(pady=5)

        self.friend_button = tk.Button(self.friends_frame, text="Add Friend", command=self.add_friend)
        self.friend_button.pack(pady=5)

        self.friend_field = tk.Entry(self.friends_frame, width=30)
        self.friend_field.pack(padx=10, pady=5)
        self.friend_field.insert(0, "Enter Friend Username")


        # buttons for chats
        self.chat_frames = {}
        self.current_chat = None

        # active users on chats
        self.active_users = {}

        self.button_frame = tk.Frame(self.left_frame)
        self.button_frame.pack(side=tk.TOP)

        self.chat_button_1 = tk.Button(self.button_frame, text="SERVER", command=lambda: self.toggle_chats("SERVER"))
        self.chat_button_1.pack(side=tk.LEFT)

        self.chat_button_2 = tk.Button(self.button_frame, text="+", command=self.create_new_chat)
        self.chat_button_2.pack(side=tk.RIGHT)
        self.chat_button_2.config(state=tk.DISABLED)

        # frame for chats
        self.chat_frame = tk.Frame(self.left_frame)
        self.chat_frame.pack(side = tk.TOP)

        self.toggle_chats("SERVER")

        # message entry
        self.below_chat_frame = tk.Frame(self.left_frame)
        self.below_chat_frame.pack(side = tk.TOP)

        self.entry_field = tk.Entry(self.below_chat_frame, width=40)
        self.entry_field.pack(padx=10, pady=10)
        self.entry_field.bind("<Return>", self.send_message)
        self.entry_field.config(state=tk.DISABLED)

        self.register_button = tk.Button(self.below_chat_frame, text="Register", command=self.register_user)
        self.register_button.pack(pady=5)

        self.login_button = tk.Button(self.below_chat_frame, text="Login", command=self.login_user)
        self.login_button.pack(pady=5)

        self.exit_button = tk.Button(self.below_chat_frame, text="Exit", command=self.exit_app)
        self.exit_button.pack(pady=5)

        # login + password
        self.login_field = tk.Entry(self.below_chat_frame, width=40)
        self.login_field.pack(padx=10, pady=5)
        self.login_field.insert(0, "Enter Username")

        self.password_field = tk.Entry(self.below_chat_frame, width=40, show="*")
        self.password_field.pack(padx=10, pady=5)
        self.password_field.insert(0, "xxxxxxxxxx")

        self.socket = None
        self.logged_in = False

        # connect to server automatically
        if not self.connect_to_server():
            self.exit_app()

    def connect_to_server(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((HOST, PORT))
            self.append_to_chat("connected to server at {}:{}".format(HOST, PORT))
            return True

        except Exception as e:
            self.append_to_chat("error connecting to server: " + str(e))
            return False
    FORBIDDEN_USERNAMES={"JOIN", "ACTIVE_USERS", "FRIENDS_LIST", "LOGIN", "REGISTER", "OK"}

    def is_keyword(self, username):
        return any(username.upper().startswith(keyword) for keyword in FORBIDDEN_USERNAMES)

    def register_user(self):
        login = self.login_field.get().strip().replace(" ", "_")
        if is_keyword(login):
            self.append_to_chat("Username cannot start with: JOIN/ACTIVE_USERS/FRIENDS_LIST/LOGIN/REGISTER/OK")
            return
        password = self.password_field.get().strip().replace(" ", "_")

        if login and password:
            message = f"REGISTER {login} {password}"
            self.socket.send(message.encode('utf-8'))
            data = self.socket.recv(1024)
            self.append_to_chat(f"[server]: {data.decode('utf-8')}")
        else:
            self.append_to_chat("Please enter a username and password.")

    def login_user(self):
        login = self.login_field.get().strip().replace(" ", "_")
        password = self.password_field.get().strip().replace(" ", "_")

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
                            self.button_frame, text=chatroom,
                            command=lambda cr=chatroom: self.toggle_chats(cr)
                        )
                        chat_button.pack(side=tk.LEFT)

                    if chatroom != "SERVER":
                        self.socket.send(f"ACTIVE_USERS {chatroom}".encode("utf-8"))
                        active_users_response = self.socket.recv(1024).decode("utf-8")
                        chat_name, users = active_users_response[12:].split(maxsplit=1)
                        self.active_users[chat_name] = users.split()

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

    def add_friend(self):
        username1 = self.login_field.get().strip().replace(" ", "_")
        username2 = self.friend_field.get().strip().replace(" ", "_")

        if username2: 
            if username1 == username2:
                self.toggle_chats("SERVER")
                self.append_to_chat("You cannot be your own friend...")
                return

            message = f"ADD_FRIEND {username2}"
            try:
                self.socket.send(message.encode('utf-8'))
                #data = self.socket.recv(1024).decode('utf-8')
                #self.append_to_chat(f"[server]: {data}")
            except Exception as e:
                self.append_to_chat(f"Error adding friend: {str(e)}")
        else:
            self.append_to_chat("Please enter a friend's username.")

    def show_friends(self):
        if self.socket:
            threading.Thread(target=self.fetch_friends, daemon=True).start()
        else:
            self.append_to_chat("You are not connected to the server.")

    def fetch_friends(self):
        username = self.login_field.get().strip().replace(" ", "_")
        try:
           
            mess = f"OK {username}" 
            self.socket.send(mess.encode("utf-8"))
        except Exception as e:
            self.append_to_chat(f"Error retrieving friends: {str(e)}")

    def get_friends(self, friends):
        self.friends_listbox.delete(0, tk.END)  # clearing to refresh
        friends_list = friends.split()
        for friend in friends_list:
            self.friends_listbox.insert(tk.END, friend)

    def receive_message(self):
        while True:
            try:
                data = self.socket.recv(1024).decode("utf-8")
                if data:
                    if data.startswith("ACTIVE_USERS"):
                        chat_name, users = data[12:].split(maxsplit = 1)
                        self.active_users[chat_name] = users.split()

                    elif data.startswith("FRIENDS_LIST:"):
                        friends_list = data[len("FRIENDS_LIST:"):].strip()
                        self.root.after(0, lambda: self.get_friends(friends_list))
                    elif data.startswith("JOIN"):
                        chat_name, user = data[4:].split(maxsplit = 1)

                        fmsg = f"{user} has joined."
                        self.active_users[chat_name].append(user)
                        self.root.after(0, lambda: self.append_to_chat(fmsg, chat_name))
                        self.root.after(0, lambda: self.show_active_users(self.active_users[chat_name]))

                    elif data.startswith("LOGOUT"):
                        chat_name, user = data[6:].split(maxsplit = 1)

                        fmsg = f"{user} has logged out."
                        self.active_users[chat_name].remove(user)
                        self.root.after(0, lambda: self.append_to_chat(fmsg, chat_name))
                        self.root.after(0, lambda: self.show_active_users(self.active_users[chat_name]))

                    else:
                        parts = data.split(maxsplit=2)
                        if len(parts) == 3:
                            sender, chat_name, message = parts
                            # No extra MESSAGE line
                            fmsg = f"[{sender}]: {message}"
                            self.root.after(0, lambda: self.append_to_chat(fmsg, chat_name))
                        else:
                            self.root.after(0, lambda: self.append_to_chat(f"Invalid message received: {data}"))
            except Exception as e:
                self.root.after(0, lambda: self.append_to_chat(f"Error receiving message: {str(e)}"))
                break

    def show_active_users(self, users):
        self.active_users_listbox.delete(0, tk.END)  # clearing to refresh
        for user in users:
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
            if name != "SERVER":
                self.active_users[name] = []

        self.show_chat(name)
        if name != "SERVER":
            self.show_active_users(self.active_users[name])

    def show_chat(self, chat_name):
        if self.current_chat:
            self.chat_frames[self.current_chat].pack_forget()

        self.chat_frames[chat_name].pack(padx=10, pady=0)

        self.current_chat = chat_name

    def create_new_chat(self):
        chat_name = simpledialog.askstring("New chat", "Enter the name for the new chat: ")
        if chat_name:
            self.toggle_chats(chat_name)

            new_chat_button = tk.Button(self.button_frame, text=chat_name, command=lambda: self.toggle_chats(chat_name))
            new_chat_button.pack(side=tk.LEFT)

            self.socket.send(bytes(f"JOIN {chat_name}", "utf-8"))
            self.socket.send(f"ACTIVE_USERS {chat_name}".encode("utf-8"))

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

# TODO: for server - disconnect client when server terminates
