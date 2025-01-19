#include <stdio.h>
#include <stdlib.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <string.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <unistd.h>
#include <pthread.h>
#include <sqlite3.h>

#define MAX_CLIENTS 100

char client_message[2000];
char buffer[1024];
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
sqlite3 *db;

int readThreadComplete = 0;

typedef struct {
    int socket;
    int logged_in;
    char login[100];
} ClientData;

ClientData clientTable[MAX_CLIENTS];

int login_exists(const char *login) {
    sqlite3_stmt *stmt;
    const char *sql = "SELECT id FROM users WHERE login = ?;";
    int rc;
    int exists = 0;

    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, 0);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Failed to prepare statement: %s\n", sqlite3_errmsg(db));
        return 0;
    }

    sqlite3_bind_text(stmt, 1, login, -1, SQLITE_STATIC);

    rc = sqlite3_step(stmt);
    if (rc == SQLITE_ROW) {
        exists = 1;  //user exists
    }

    sqlite3_finalize(stmt);
    return exists;
}

int chatroom_exists(const char *chatName) {
    sqlite3_stmt *stmt;
    const char *sql = "SELECT id FROM chatrooms WHERE chatroom = ?;";
    int rc;
    int exists = 0;

    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, 0);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Failed to prepare statement chatrooms: %s\n", sqlite3_errmsg(db));
        return 0;
    }

    sqlite3_bind_text(stmt, 1, chatName, -1, SQLITE_STATIC);

    rc = sqlite3_step(stmt);
    if (rc == SQLITE_ROW) {
        exists = 1;  //chatroom exists
    }

    sqlite3_finalize(stmt);
    return exists;
}

int user_chatroom_exists(const char *login, const char *chatName) {
    sqlite3_stmt *stmt;
    const char *sql = "SELECT 1 FROM user_chatrooms WHERE user = ? AND chatroom = ? ;";
    int rc;
    int exists = 0;

    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, 0);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Failed to prepare statement user_chatrooms: %s\n", sqlite3_errmsg(db));
        return 0;
    }

    sqlite3_bind_text(stmt, 1, login, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, chatName, -1, SQLITE_STATIC);

    rc = sqlite3_step(stmt);
    if (rc == SQLITE_ROW) {
        exists = 1;  //chatroom exists
    }

    sqlite3_finalize(stmt);
    return exists;
}

int validate_login(const char *login, const char *password) {
    sqlite3_stmt *stmt;
    const char *sql = "SELECT password FROM users WHERE login = ?;";
    int rc;
    const char *stored_password;

    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, 0);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "stmt error: %s\n", sqlite3_errmsg(db));
        return 0;
    }

    sqlite3_bind_text(stmt, 1, login, -1, SQLITE_STATIC);

    rc = sqlite3_step(stmt);
    if (rc == SQLITE_ROW) {
        stored_password = (const char *)sqlite3_column_text(stmt, 0);
        if (stored_password && strcmp(stored_password, password) == 0) {
            sqlite3_finalize(stmt);
            return 1;  //login ok
        }
    }

    sqlite3_finalize(stmt);
    return 0;  
}

int findEmptyClientSlot() {
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clientTable[i].socket == 0) {
            return i;
        }
    }
    return -1;
}

int clearClientSlot(int clientSocket) {
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clientTable[i].socket == clientSocket) {
            clientTable[i].socket = 0;
            clientTable[i].logged_in = 0;
            memset(clientTable[i].login, 0, sizeof(clientTable[i].login));
            return 1;
        }
    }
    return 0;
}

void sendMessageToAllClients(char *message, ClientData *client) {
    // ME WHEN STRINGS .___________________________.
    int bufferSize = strlen(message) + strlen(client->login) + 2;

    // because strtok destroys the string...
    char *messagecopy = (char *)malloc(strlen(message));
    memset(messagecopy, 0, strlen(message));

    strncpy(messagecopy, message, strlen(message));

    char *room = strtok(message, " ");
   
    char *formattedMsg = (char *)malloc(bufferSize);
    memset(formattedMsg, 0, bufferSize);

    snprintf(formattedMsg, bufferSize, "%s %s", client->login, messagecopy);
    printf("MESSAGE: %s\n", formattedMsg);
   
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clientTable[i].socket != 0 && user_chatroom_exists(clientTable[i].login, room)) {
            printf("[send to client on slot %d on socket %d]: %s\n",i, clientTable[i].socket, formattedMsg);
            send(clientTable[i].socket, formattedMsg, strlen(formattedMsg), 0);  // format: LOGIN CHATROOM MESSAGE
        }
    }
    free(formattedMsg);
}

void *socketThread(void *arg) {
    ClientData *client = (ClientData *)arg;
    int n;
    char *login;
    char *password;
    char *errMsg = 0;
    char *chatroom_name;
    int rc;

    while (1) {
        n = recv(client->socket, client_message, 2000, 0);
        if (n < 1) {
            printf("[client logged out]\n");
            break;
        }

        printf("[message from client]: %s\n", client_message);

        if (strncmp(client_message, "REGISTER", 8) == 0) {
            login = strtok(client_message + 9, " "); // cut register string
            password = strtok(NULL, " ");  

            if (login && password) {
                if (login_exists(login)) {
                    send(client->socket, "Login is already taken :(", 21, 0);
                } else {
                    char sql[200];
                    snprintf(sql, sizeof(sql), "INSERT INTO users (login, password) VALUES ('%s', '%s');", login, password);

                    rc = sqlite3_exec(db, sql, 0, 0, &errMsg);
                    if (rc != SQLITE_OK) {
                        fprintf(stderr, "SQL error: %s\n", errMsg);
                        sqlite3_free(errMsg);
                        send(client->socket, "registration failed.", 20, 0);
                    } else {
                        send(client->socket, "registration successful.", 23, 0);
                    }
                }
            } else {
                send(client->socket, "invalid data.", 26, 0);
            }
        }
        else if (strncmp(client_message, "LOGIN", 5) == 0) {
            login = strtok(client_message + 6, " ");
            password = strtok(NULL, " ");

            if (login && password) {
                if (validate_login(login, password)) {
                   
                    int clientSlot = findEmptyClientSlot();
                    if (clientSlot >= 0) {
                client->logged_in = 1;
                strncpy(client->login, login, sizeof(client->login) - 1);

                clientTable[clientSlot] = *client;

                // chatrooms user already has
                sqlite3_stmt *stmt;
                const char *sql = "SELECT chatroom FROM user_chatrooms WHERE user = ?;";
                rc = sqlite3_prepare_v2(db, sql, -1, &stmt, 0);
                if (rc == SQLITE_OK) {
                    sqlite3_bind_text(stmt, 1, login, -1, SQLITE_STATIC);

                    char chatrooms[1024] = "login successful:";
                    while (sqlite3_step(stmt) == SQLITE_ROW) {
                        const char *chatroom = (const char *)sqlite3_column_text(stmt, 0);
                        strcat(chatrooms, " ");
                        strcat(chatrooms, chatroom);
                    }
                    sqlite3_finalize(stmt);

                    send(client->socket, chatrooms, strlen(chatrooms), 0);
                } else {
                    send(client->socket, "error fetching chatrooms", 24, 0);
                }
            } else {
                send(client->socket, "reached maximum number of users", 32, 0);
            }
        } else {
            send(client->socket, "invalid login/password.", 27, 0);
        }
    } else {
        send(client->socket, "error", 20, 0);
    }
}
        else if (strncmp(client_message, "JOIN", 4) == 0) {
            chatroom_name = strtok(client_message + 5, " ");

            if (!chatroom_exists(chatroom_name)) {
                char sql[200];
                snprintf(sql, sizeof(sql), "INSERT INTO chatrooms (chatroom) VALUES ('%s');", chatroom_name);

                rc = sqlite3_exec(db, sql, 0, 0, &errMsg);
                if (rc != SQLITE_OK) {
                    fprintf(stderr, "SQL error: %s\n", errMsg);
                    sqlite3_free(errMsg);
                }
            }

            if(!user_chatroom_exists(client->login, chatroom_name)) {
                char sql[200];
                snprintf(sql, sizeof(sql), "INSERT INTO user_chatrooms (user, chatroom) VALUES ('%s', '%s');", client->login, chatroom_name);
                rc = sqlite3_exec(db, sql, 0, 0, &errMsg);
                if (rc != SQLITE_OK) {
                    fprintf(stderr, "SQL error: %s\n", errMsg);
                    sqlite3_free(errMsg);
                }

            }

            // send(client->socket, "SERVER Joined new room!", 24, 0);

        }

        else if (strncmp(client_message, "GET_ACTIVE_USERS", 16) == 0) {
            char activeUsers[1024] = "ACTIVE_USERS:";
            for (int i = 0; i < MAX_CLIENTS; i++) {
                if (clientTable[i].socket != 0 && clientTable[i].logged_in) {
                    strcat(activeUsers, " ");
                    strcat(activeUsers, clientTable[i].login);
                }
            }
            send(client->socket, activeUsers, strlen(activeUsers), 0);
        }
       
        else if (client->logged_in) {
            sendMessageToAllClients(client_message, client);
        } else {
            send(client->socket, "you must log in first!", 22, 0);
        }

        memset(&client_message, 0, sizeof(client_message));
    }

    pthread_mutex_lock(&lock);
    readThreadComplete = 1;
    pthread_mutex_unlock(&lock);

    clearClientSlot(client->socket);
    close(client->socket);
    free(client);
    pthread_exit(NULL);
}

int main() {
    int serverSocket, newSocket;
    struct sockaddr_in serverAddr;
    struct sockaddr_storage serverStorage;
    socklen_t addr_size;
    int rc;
    char *errMsg = 0;

    rc = sqlite3_open("users.db", &db);
    if (rc) {
        fprintf(stderr, "can't open db: %s\n", sqlite3_errmsg(db));
        return 1;
    }

    char *sql = "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT, password TEXT);";
    rc = sqlite3_exec(db, sql, 0, 0, &errMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL error: %s\n", errMsg);
        sqlite3_free(errMsg);
        sqlite3_close(db);
        return 1;
    }

    sql = "CREATE TABLE IF NOT EXISTS chatrooms (id INTEGER PRIMARY KEY AUTOINCREMENT, chatroom TEXT);";
    rc = sqlite3_exec(db, sql, 0, 0, &errMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL error: %s\n", errMsg);
        sqlite3_free(errMsg);
        sqlite3_close(db);
        return 1;
    }

    sql = "CREATE TABLE IF NOT EXISTS user_chatrooms (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, chatroom TEXT,"
                                                            "FOREIGN KEY (user) REFERENCES users(login),"
                                                            "FOREIGN KEY (chatroom) REFERENCES chatrooms(chatroom));";
    rc = sqlite3_exec(db, sql, 0, 0, &errMsg);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "SQL error: %s\n", errMsg);
        sqlite3_free(errMsg);
        sqlite3_close(db);
        return 1;
    }

    serverSocket = socket(PF_INET, SOCK_STREAM, 0);
    if (serverSocket < 0) {
        perror("Socket creation failed");
        return 1;
    }

    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(1100);
    serverAddr.sin_addr.s_addr = htonl(INADDR_ANY);

    memset(serverAddr.sin_zero, '\0', sizeof serverAddr.sin_zero);

    rc = bind(serverSocket, (struct sockaddr *)&serverAddr, sizeof(serverAddr));
    if (rc < 0) {
        perror("Bind failed");
        close(serverSocket);
        sqlite3_close(db);
        return 1;
    }

    if (listen(serverSocket, 50) == 0)
        printf("Listening...\n");
    else {
        printf("Error\n");
        close(serverSocket);
        sqlite3_close(db);
        return 1;
    }

    pthread_t thread_id;

    while (1) {
        addr_size = sizeof serverStorage;
        newSocket = accept(serverSocket, (struct sockaddr *)&serverStorage, &addr_size);
        if (newSocket < 0) {
            perror("Accept failed");
            continue;
        }

        ClientData *client = (ClientData *)malloc(sizeof(ClientData));
        client->socket = newSocket;
        client->logged_in = 0;

        if (pthread_create(&thread_id, NULL, socketThread, client) != 0) {
            printf("Failed to create thread\n");
            close(newSocket);
            free(client);
            continue;
        }

        pthread_detach(thread_id);
    }

    sqlite3_close(db);
    close(serverSocket);
    return 0;
}