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
	}
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {

	signalChan := make(chan os.Signal, 1)
	signal.Notify(signalChan, syscall.SIGTERM)

	go func() {
		<-signalChan
		log.Infof("action: signal_received | result: success | client_id: %v", c.config.ID)
		if c.conn != nil {
			c.conn.Close()
			log.Infof("action: close_socket | result: success | client_id: %v", c.config.ID)
		}
		os.Exit(0)
	}()

	// There is an autoincremental msgID to identify every message sent
	// Messages if the message amount threshold has not been surpassed
	for msgID := 1; msgID <= c.config.LoopAmount; msgID++ {
		// Create the connection the server in every loop iteration. Send an
		c.createClientSocket()

		if c.conn == nil {
			log.Errorf("action: connect | result: fail | client_id: %v", c.config.ID)
			return
		}

		nombre := os.Getenv("NOMBRE")
		apellido := os.Getenv("APELLIDO")
		documento := os.Getenv("DOCUMENTO")
		nacimiento := os.Getenv("NACIMIENTO")
		numero := os.Getenv("NUMERO")

		// Construyo el mensaje de protocolo con formato clave=valor|
		protocolMsg := fmt.Sprintf("NOMBRE=%s|APELLIDO=%s|DOCUMENTO=%s|NACIMIENTO=%s|NUMERO=%s\n",
		nombre, apellido, documento, nacimiento, numero)

		_, err := c.conn.Write([]byte(protocolMsg))
		if err != nil {
			log.Errorf("action: send_message | result: fail | client_id: %v | error: %v",
				c.config.ID,
				err,
			)
			return
		}

		// Leer la respuesta
		msgReader := bufio.NewReader(c.conn)
		reponse, err := msgReader.ReadString('\n')
		c.conn.Close()

		if err != nil {
			log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
				c.config.ID,
				err,
			)
			return
		}

		log.Infof("action: receive_message | result: success | client_id: %v | msg: %v",
			c.config.ID,
			reponse,
		)

		log.Infof("action: apuesta_enviada | result: success | dni: %v | numero: %v",
			documento,
			numero,
		)

		// Wait a time between sending one message and the next one
		time.Sleep(c.config.LoopPeriod)

	}
	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}
