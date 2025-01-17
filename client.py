import socket
import tkinter as tk
from tkinter import scrolledtext

HOST = "127.0.0.1"
PORT = 1100

class SocketClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Socket Client")

        self.chat_display = scrolledtext.ScrolledText(self.root, height=20, width=50, wrap=tk.WORD)
        self.chat_display.pack(padx=10, pady=10)
        self.chat_display.config(state=tk.DISABLED)

        self.entry_field = tk.Entry(self.root, width=40)
        self.entry_field.pack(padx=10, pady=10)
        self.entry_field.bind("<Return>", self.send_message)  
        self.connect_button = tk.Button(self.root, text="Connect", command=self.connect_to_server)
        self.connect_button.pack(pady=5)

        self.socket = None

    def connect_to_server(self):
        """Connect to the server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((HOST, PORT))
            self.append_to_chat("Connected to server at {}:{}".format(HOST, PORT))
        except Exception as e:
            self.append_to_chat("Error connecting to server: " + str(e))

    def send_message(self, event=None):
        """Send message to the server"""
        msg = self.entry_field.get().strip()
        if msg == "exit":
            self.append_to_chat("Connection closed.")
            if self.socket:
                self.socket.close()
            self.root.quit()
            return
        if self.socket:
            try:
                self.socket.send(bytes(msg, "utf-8"))
                data = self.socket.recv(1024)
                self.append_to_chat("You: " + msg)
                self.append_to_chat("Server: " + data.decode("utf-8"))
            except Exception as e:
                self.append_to_chat("Error: " + str(e))
        self.entry_field.delete(0, tk.END)

    def append_to_chat(self, text):
        """Append text to the chat display"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, text + "\n")
        self.chat_display.yview(tk.END)  # Scroll to the bottom
        self.chat_display.config(state=tk.DISABLED)

def run_app():
    root = tk.Tk()
    app = SocketClientApp(root)
    root.mainloop()

if __name__ == "__main__":
    run_app()
