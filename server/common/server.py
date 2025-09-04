import socket
import logging
import signal
from common.communication import read_n, write_all
from common.bet import deserialize_batch
from common.utils import Bet, store_bets

class Server:
    def __init__(self, port, listen_backlog):
        
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._shutdown = False
        self._client_sockets = []

        signal.signal(signal.SIGTERM, self._handle_sigterm)

    # handle_sigterm se encarga de manejar la señal SIGTERM para un apagado ordenado
    def _handle_sigterm(self, signum, frame):
        logging.info("action: handle_sigterm | result: success")
        self._shutdown_server()

    # _shutdown_server cierra el socket del servidor y todos los sockets de clientes conectados
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

    # run acepta conexiones entrantes y maneja cada conexión en un hilo separado
    def run(self):
        while not self._shutdown:
            try:
                client_sock = self.__accept_new_connection()
                if client_sock:
                    self.__handle_client_connection(client_sock)
            except OSError as e:
                logging.error(f"action: run | result: fail | error: {e}")
                break

    # __handle_client_connection maneja la conexión de un cliente, recibe el mensaje y lo procesa
    def __handle_client_connection(self, client_sock):
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

    # _receive_message recibe el mensaje del cliente, lo deserializa y almacena la apuesta
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

            decoded = data.decode().strip()
            try:
                raw_bets = deserialize_batch(decoded)
                bet_objects = []

                for bet in raw_bets:
                    nombre, apellido, dni, nacimiento, numero, agencia = bet
                    bet_obj = Bet(agencia, nombre, apellido, dni, nacimiento, numero)
                    bet_objects.append(bet_obj)

                store_bets(bet_objects)
                logging.info(f"action: apuesta_recibida | result: success | cantidad: {len(bet_objects)}")
                write_all(client_sock, b"OK")

            except Exception as e:
                count_str = decoded.split('|')[1] if decoded.startswith("count|") else "?"
                logging.info(f"action: apuesta_recibida | result: fail | cantidad: {count_str} | error: {e}")
                write_all(client_sock, b"ER")

        except Exception as e:
            logging.error(f"action: process_batch | result: fail | error: {e}")

    # __accept_new_connection acepta una nueva conexión entrante
    def __accept_new_connection(self):
        logging.info('action: accept_connections | result: in_progress')
        c, addr = self._server_socket.accept()
        logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        return c
