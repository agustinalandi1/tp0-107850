import socket
import logging
import signal
import threading
from common.communication import read_n, write_all
from common.bet import deserialize_batch
from common.utils import Bet, store_bets, load_bets, has_won
import os

class Server:
    def __init__(self, port, listen_backlog):

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._shutdown = False
        self._client_sockets = []
        self._finished_clients = 0
        self._expected_clients = int(os.environ.get("EXPECTED_CLIENTS", 5))  # fallback por si no se setea
        self._winners_by_agency = {}
        self._draw_done = False
        self._bets_lock = threading.Lock()
        self._draw_lock = threading.Lock()
        self._client_threads = []

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
        try:
            self._server_socket.close()
        except Exception as e:
            logging.error(f"action: close_server_socket | result: fail | error: {e}")
        for socket in self._client_sockets:
            try:
                socket.close()
            except Exception as e:
                logging.error(f"action: close_client_socket | result: fail | error: {e}")
        for t in self._client_threads:
            t.join()
            logging.info("action: join_client_thread | result: success")
    
    def run(self):
        while not self._shutdown:
            try:
                client_sock = self.__accept_new_connection()
                if client_sock:
                    thread = threading.Thread(
                        target=self.__handle_client_connection,
                        args=(client_sock,)
                    )
                    thread.start()
                    self._client_threads.append(thread)
            except OSError as e:
                logging.error(f"action: run | result: fail | error: {e}")
                break

    # __handle_client_connection maneja la conexión de un cliente, recibe el mensaje y lo procesa
    def __handle_client_connection(self, client_sock):
        self._client_sockets.append(client_sock)
        try:
            while not self._shutdown:
                if not self._receive_message(client_sock):
                    break
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
                return False

            decoded_message = data.decode().strip()
            if not decoded_message:
                logging.debug("action: receive_message | result: success | status: empty_message_ignored")
                return

            if decoded_message.startswith("FIN|"):
                self._handle_end_notification(client_sock, decoded_message)
            elif decoded_message.startswith("WINNERS|"):
                self._handle_winners_request(client_sock, decoded_message)
            else:
                self._handle_bet_batch(client_sock, decoded_message)

        except Exception as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")
            try:
                write_all(client_sock, b"ER\n")
            except:
                pass
        return True

    # __accept_new_connection acepta una nueva conexión entrante, devuelve el socket del cliente
    def __accept_new_connection(self):
        c, addr = self._server_socket.accept()
        logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        return c

    # _handle_bet_batch procesa un lote de apuestas, las almacena y responde al cliente
    def _handle_bet_batch(self, client_sock, decoded):
        try:
            raw_bets = deserialize_batch(decoded)
            bet_objects = []

            for bet in raw_bets:
                first_name, last_name, document, birthdate, number, agency = bet
                bet_obj = Bet(agency, first_name, last_name, document, birthdate, number)
                bet_objects.append(bet_obj)

            with self._bets_lock:
                store_bets(bet_objects)
            logging.info(f"action: apuesta_recibida | result: success | cantidad: {len(bet_objects)}")
            write_all(client_sock, b"OK\n")
            return True

        except Exception as e:
            logging.info(f"action: apuesta_recibida | result: fail | error: {e}")
            write_all(client_sock, b"ER\n")
            return True

    # _normalize_agency normaliza el identificador de la agencia dejando solo dígitos. EJ: "agencia-01" -> "01", "client1" -> "1"
    def _normalize_agency(self, raw):
        return ''.join(ch for ch in str(raw) if ch.isdigit())
    
    # _handle_end_notification maneja la notificación de fin de apuestas de una agencia, actualiza el conteo y realiza el sorteo si es necesario
    def _handle_end_notification(self, client_sock, message):
        try:
            _, agency = message.split("|", 1)
            agency = self._normalize_agency(agency)

            with self._draw_lock:
                self._finished_clients += 1
                logging.info(f"action: end_of_bets | result: success | agency: {agency}")
                if self._finished_clients == self._expected_clients and not self._draw_done:
                    self._perform_draw()
            write_all(client_sock, b"OK\n")    
            return True

        except Exception as e:
            logging.error(f"action: handle_end_notification | result: fail | error: {e}")
            write_all(client_sock, b"ER\n")
            return True

    # _perform_draw realiza el sorteo, determina los ganadores y los agrupa por agencia
    def _perform_draw(self):
        self._winners_by_agency = {}

        for bet in load_bets():
            if has_won(bet):
                key = self._normalize_agency(bet.agency)
                self._winners_by_agency.setdefault(key, []).append(bet.document)

        self._draw_done = True
        logging.info(f"action: draw_results | result: success | winners_by_agency: {self._winners_by_agency}")

    # _handle_winners_request maneja la solicitud de ganadores de una agencia, responde con la lista de ganadores
    # o espera si el sorteo no se ha realizado
    def _handle_winners_request(self, client_sock, message):
        try:
            with self._draw_lock:
                if not self._draw_done:
                    write_all(client_sock, b"WAIT\n")
                    return True

                _, agency = message.split("|", 1)
                agency = self._normalize_agency(agency)
                winners = self._winners_by_agency.get(agency, [])
                response = "WINNERS\n" if not winners else "WINNERS|" + "|".join(winners) + "\n"
            
            write_all(client_sock, response.encode())
            logging.info(f"action: winners_request | result: success | agency: {agency} | winners_count: {len(winners)}")
            return True
        
        except Exception as e:
            logging.error(f"action: winners_request | result: fail | error: {e}")
            write_all(client_sock, b"ER\n")
            return True

