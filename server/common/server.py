import socket
import logging
import signal
from common import utils

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)

        def handle_sigterm(signum, frame):
            logging.info("action: handle_sigterm | result: success")
            self._server_socket.close()
            logging.info("action: close_server_socket | result: success")
            exit(0)
        
        signal.signal(signal.SIGTERM, handle_sigterm)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        # TODO: Modify this program to handle signal to graceful shutdown
        # the server
        while True:
            client_sock = self.__accept_new_connection()
            self.__handle_client_connection(client_sock)

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            data = b""
            while not data.endswith(b"\n"):
                chunk = client_sock.recv(1024)
                if not chunk:
                    break
                data += chunk
            msg = data.rstrip().decode('utf-8')

            # Parseo el protocolo
            campos = dict(item.split("=", 1) for item in msg.split("|") if "=" in item)
            nombre = campos.get("NOMBRE", "")
            apellido = campos.get("APELLIDO", "")  
            documento = campos.get("DOCUMENTO", "")
            nacimiento = campos.get("NACIMIENTO", "")
            numero = campos.get("NUMERO", "")
            
            bet = utils.Bet(
                agency = 1,
                first_name = nombre,
                last_name = apellido,
                document = documento,
                birthdate = nacimiento,
                number = numero
            )

            utils.store_bets([bet])
            logging.info(f'action: apuesta_almacenada | result: success | dni: {documento} | numero: {numero}')
            client_sock.sendall(b"OK\n")

        except Exception as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            client_sock.close()

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        c, addr = self._server_socket.accept()
        logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        return c
