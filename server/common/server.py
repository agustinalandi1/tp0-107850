import socket
import logging
import signal
from common.communication import read_n, write_all
from common.bet import deserialize_batch
from common.utils import Bet, store_bets, load_bets, has_won

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._shutdown = False
        self._client_sockets = []
        self._notified_agencies = set()
        self._winners_by_agency = {}
        self._draw_done = False

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

            decoded = data.decode().strip()            
            if decoded.startswith("count|"):
                self._handle_bet_batch(client_sock, decoded)

            elif decoded.startswith("FIN|"):
                self._handle_end_notification(client_sock, decoded)

            elif decoded.startswith("WINNERS|"):
                self._handle_winners_request(client_sock, decoded)

            else:
                logging.warning(f"action: unknown_message | result: ignored | content: {decoded}")
                write_all(client_sock, b"ER\n")

        except Exception as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")
            write_all(client_sock, b"ER\n")

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

    def _handle_bet_batch(self, client_sock, decoded):
        try:
            raw_bets = deserialize_batch(decoded)
            bet_objects = []

            for bet in raw_bets:
                first_name, last_name, document, birthdate, number, agency = bet
                bet_obj = Bet(agency, first_name, last_name, document, birthdate, number)
                bet_objects.append(bet_obj)

            store_bets(bet_objects)
            logging.info(f"action: bets_received | result: success | amount: {len(bet_objects)}")
            write_all(client_sock, b"OK\n")

        except Exception as e:
            count_str = decoded.split('|')[1] if decoded.startswith("count|") else "?"
            logging.info(f"action: bets_received | result: fail | amount: {count_str} | error: {e}")
            write_all(client_sock, b"ER\n")

    def _handle_end_notification(self, client_sock, message):
        try:
            _, agency = message.split("|")
            self._notified_agencies.add(agency)
            logging.info(f"action: end_of_bets | result: success | agency: {agency}")
            write_all(client_sock, b"OK\n")

            logging.info(f"DEBUG SERVER agencias notificadas hasta ahora: {self._notified_agencies}")
            if len(self._notified_agencies) == 5 and not self._draw_done:
                self._perform_draw()

        except Exception as e:
            logging.error(f"action: handle_end_notification | result: fail | error: {e}")
            write_all(client_sock, b"ER\n")

    def _perform_draw(self):
        self._winners_by_agency = {}

        for bet in load_bets():
            if has_won(bet):
                self._winners_by_agency.setdefault(str(bet.agency), []).append(bet.document)

        self._draw_done = True
        logging.info("action: draw | result: success")

    def _handle_winners_request(self, client_sock, message):
        try:
            if not self._draw_done:
                write_all(client_sock, b"WAIT\n")
                return

            _, agency = message.split("|")
            winners = self._winners_by_agency.get(agency, [])
            response = "WINNERS|" + "|".join(winners) + "\n"
            write_all(client_sock, response.encode())

            logging.info(f"action: winners_request | result: success | agency: {agency} | winners_count: {len(winners)}")

        except Exception as e:
            logging.error(f"action: winners_request | result: fail | error: {e}")
            write_all(client_sock, b"ER\n")

