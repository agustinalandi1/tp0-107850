import socket
import logging
import signal
from common.communication import read_n, write_all
from common.bet import deserialize_bet
from common.utils import Bet, store_bets

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._shutdown = False
        self._client_sockets = []

        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigterm(self, signum, frame):
        logging.info("action: handle_sigterm | result: success")
        self._shutdown_server()

    def _shutdown_server(self):
        if self._shutdown:
            return
        self._shutdown = True

        logging.info("action: shutdown | result: in_progress")

        try:
            self._server_socket.close()
            logging.info("action: close_server_socket | result: success")
        except Exception as e:
            logging.error(f"action: close_server_socket | result: fail | error: {e}")

        for sock in self._client_sockets:
            try:
                sock.close()
                logging.info("action: close_client_socket | result: success")
            except Exception as e:
                logging.error(f"action: close_client_socket | result: fail | error: {e}")

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """
        while not self._shutdown:
            try:
                client_sock = self.__accept_new_connection()
                if client_sock:
                    self.__handle_client_connection(client_sock)
            except OSError as e:
                logging.error(f"action: run | result: fail | error: {e}")
                break

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        self._client_sockets.append(client_sock)
        try:
            self._receive_message(client_sock)
        finally:
            try:
                client_sock.close()
            except Exception:
                pass
            if client_sock in self._client_sockets:
                self._client_sockets.remove(client_sock)

    def _receive_message(self, client_sock):
        try:
            data = b""
            while not data.endswith(b"\n"):
                chunk = client_sock.recv(1024)
                if not chunk:
                    break
                data += chunk
            if not data:
                return None

            logging.debug(f"DEBUG SERVER raw_data: {repr(data)}")
            logging.debug(f"DEBUG SERVER decoded_data: {data.decode()}")
            nombre, apellido, dni, nacimiento, numero, agencia = deserialize_bet(data.decode())
            bet = Bet(agencia, nombre, apellido, dni, nacimiento, numero)
            store_bets([bet])
            logging.info(f"action: apuesta_almacenada | result: success | dni: {dni} | numero: {numero}")
            write_all(client_sock, b"OK")

        except Exception as e:
           logging.error(f"action: process_bet | result: fail | error: {e}")

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
