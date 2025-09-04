package common

import (
	"bufio"
	"fmt"
	"net"
	"time"
	"os"
	"os/signal"
	"syscall"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	conn   net.Conn
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}
	c.conn = conn
	return nil
}

// closeClientSocket closes the client socket if it is open
func (c *Client) closeClientSocket() {
	if c.conn != nil {
		c.conn.Close()
		log.Infof("action: close_socket | result: success | client_id: %v", c.config.ID)
		c.conn = nil
	}
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {

	// channel de señales del SO (buffer 1 para no perder la señal)
	signalsChannel := make(chan os.Signal, 1)
	signal.Notify(signalsChannel, os.Interrupt, syscall.SIGTERM)
	defer signal.Stop(signalsChannel) // deja de recibir señales cuando sale

	// There is an autoincremental msgID to identify every message sent
	// Messages if the message amount threshold has not been surpassed
	for msgID := 1; msgID <= c.config.LoopAmount; msgID++ {

		// Salida graceful si llega una señal antes de abrir
		select {
		case <-signalsChannel:
			// Cierro lo que haya abierto y termino ordenadamente
			if c.conn != nil {
				_ = c.conn.Close()
				log.Infof("action: close_socket | result: success | client_id: %v", c.config.ID)
			}
			log.Infof("action: client_shutdown | result: success | client_id: %v", c.config.ID)
			return
		default:

			// Create the connection the server in every loop iteration. Send an
			err := c.createClientSocket()
			if err != nil {
				time.Sleep(1 * time.Second)
				continue
			}

			msg := fmt.Sprintf("[CLIENT %v] Message N°%v\n", c.config.ID, msgID)
			_, err = c.conn.Write([]byte(msg))
			if err != nil {
				log.Errorf("action: send_message | result: fail | client_id: %v | error: %v", c.config.ID, err)
				c.closeClientSocket()
				continue
			}

			// Leer la respuesta
			msgReader := bufio.NewReader(c.conn)
			reponse, err := msgReader.ReadString('\n')
			c.closeClientSocket()

			if err != nil {
				log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				continue
			}

			log.Infof("action: receive_message | result: success | client_id: %v | msg: %v",
				c.config.ID,
				reponse,
			)
		}

		// Wait a time between sending one message and the next one
		time.Sleep(c.config.LoopPeriod)

	}
	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}
