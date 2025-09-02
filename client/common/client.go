package common

import (
	"net"
	"time"
	"os"
	"os/signal"
	"syscall"

	"github.com/op/go-logging"
	"github.com/7574-sistemas-distribuidos/docker-compose-init/client/common/bet"
	"github.com/7574-sistemas-distribuidos/docker-compose-init/client/common/communication"
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
	conn net.Conn
	terminate bool
	signalChan chan os.Signal
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
		signalChan: make(chan os.Signal, 1),
	}
	signal.Notify(client.signalChan, syscall.SIGTERM)
	go client.handleSigterm()
	return client
}

func (c *Client) handleSigterm() {
	<-c.signalChan
	log.Infof("action: signal_received | result: success | client_id: %v", c.config.ID)
	c.terminate = true
	c.closeClientSocket()
	log.Infof("action: shutdown | result: success | client_id: %v", c.config.ID)
	os.Exit(0)
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
		return err
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

// sendBetWithRetry intenta enviar una apuesta con reintentos
func (client *Client) sendBetWithRetry(message, dni, numero string) bool {
	const MAX_RETRIES = 3

	for attempt := 1; attempt <= MAX_RETRIES; attempt++ {
		err := client.createClientSocket()
		if err != nil {
			log.Errorf("action: connect_attempt | result: fail | attempt: %d | error: %v", attempt, err)
			time.Sleep(1 * time.Second)
			continue
		}

		err = communication.SendMessage(client.conn, message)
		if err != nil {
			log.Errorf("action: send_message | result: fail | attempt: %d | error: %v", attempt, err)
			client.closeClientSocket()
			time.Sleep(500 * time.Millisecond)
			continue
		}

		err = communication.ReceiveAck(client.conn)
		client.closeClientSocket()

		if err != nil {
			log.Errorf("action: receive_ack | result: fail | attempt: %d | error: %v", attempt, err)
			time.Sleep(500 * time.Millisecond)
			continue
		}

		return true
	}

	return false
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {

	// There is an autoincremental msgID to identify every message sent
	// Messages if the message amount threshold has not been surpassed
	for msgID := 1; msgID <= c.config.LoopAmount; msgID++ {

		if c.terminate {
			log.Infof("action: loop_terminated | result: by_signal | client_id: %v", c.config.ID)
			break
		}

		message, dni, numero := bet.BuildBetMessage(c.config.ID)
		success := c.sendBetWithRetry(message, dni, numero)
		if success {
			log.Infof("action: apuesta_enviada | result: success | dni: %v | numero: %v",
				dni,
				numero,
			)
		} else {
			log.Errorf("action: apuesta_enviada | result: fail | dni: %v | numero: %v",
				dni,
				numero,
			)
		}

		time.Sleep(c.config.LoopPeriod)

	}
	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}
