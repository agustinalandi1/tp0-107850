package common

import (
	"net"
	"time"
	"os"
	"os/signal"
	"syscall"
	"io"
	"fmt"
	"strings"

	"github.com/op/go-logging"
	"github.com/7574-sistemas-distribuidos/docker-compose-init/client/common/bet"
	"github.com/7574-sistemas-distribuidos/docker-compose-init/client/common/communication"
)

var log = logging.MustGetLogger("log")

const (
	MaxRetries            = 3                      // reintentos por batch
	RetryConnectDelay     = 1 * time.Second        // espera tras fallo de connect
	RetryIOErrorDelay     = 500 * time.Millisecond // espera tras fallo de send/ack
	DefaultBatchMaxAmount = 15                     // fallback de tamaño de batch
)

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
	BatchMaxAmount int
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

// sendWithAckRetry sends a message and waits for an acknowledgment, retrying on failure, 
// logging each attempt
func (c *Client) sendWithAckRetry(msg string, context string) bool {
	for attempt := 1; attempt <= MaxRetries; attempt++ {
		err := communication.SendMessage(c.conn, msg)
		if err != nil {
			log.Errorf("action: send_message | result: fail | attempt: %d | error: %v", attempt, err)
			time.Sleep(RetryIOErrorDelay)
			continue
		}

		err = communication.ReceiveAck(c.conn)
		if err != nil {
			log.Errorf("action: receive_ack | result: fail | attempt: %d | error: %v", attempt, err)
			time.Sleep(RetryIOErrorDelay)
			continue
		}

		log.Infof("action: send_message | result: success")
		return true
	}
	log.Errorf("action: send_message | result: fail")
	return false
}

// sendAndReadUntilPrefix sends a message and reads the response until it matches the expected prefix, retrying on failure
func (c *Client) sendAndReadUntilPrefix(msg string, expectedPrefix string, context string) (string, bool) {
	for attempt := 1; attempt <= MaxRetries; attempt++ {
		err := communication.SendMessage(c.conn, msg)
		if err != nil {
			log.Errorf("action: send_message | result: fail | attempt: %d | error: %v", attempt, err)
			time.Sleep(RetryIOErrorDelay)
			continue
		}

		resp, err := communication.ReadMessage(c.conn)
		if err != nil {
			log.Errorf("action: read_response | result: fail | attempt: %d | error: %v", attempt, err)
			time.Sleep(RetryIOErrorDelay)
			continue
		}

		resp = strings.TrimSpace(resp)
		if resp == "WAIT" {
			log.Infof("action: read_response | result: in_progress")
			time.Sleep(RetryIOErrorDelay)
			continue
		}

		if strings.HasPrefix(resp, expectedPrefix) {
			log.Infof("action: read_response | result: success")
			return resp, true
		}

		time.Sleep(RetryIOErrorDelay)
	}
	log.Errorf("action: read_response | result: fail")
	return "", false
}

// sendBatchWithRetry sends a batch message with retries on failure
func (c *Client) sendBatchWithRetry(batchMessage string) bool {
	return c.sendWithAckRetry(batchMessage, "batch")
}

// sendBatchesFromParser reads batches from the parser and sends them, logging the results
func (c *Client) sendBatchesFromParser(parser *bet.Parser) {
	batchIndex := 0

	for {
		batch, err := parser.NextBatch()
		if err == io.EOF {
			break
		}
		if err != nil {
			log.Errorf("action: read_batch | result: fail | error: %v", err)
			continue
		}

		message := bet.SerializeBatch(batch) + "\n"
		success := c.sendBatchWithRetry(message)

		if success {
			log.Infof("action: batch_enviado | result: success | client_id: %v | index: %d | size: %d",
				c.config.ID, batchIndex, len(message))
		} else {
			log.Errorf("action: batch_enviado | result: fail | client_id: %v | index: %d | size: %d",
				c.config.ID, batchIndex, len(message))
		}
		batchIndex++
		time.Sleep(c.config.LoopPeriod)
	}
	log.Infof("action: total_batches_sent | result: success | count: %d | client_id: %v", batchIndex, c.config.ID)
}

// notifyEndOfBets notifica el final de las apuestas al servidor
func (c *Client) notifyEndOfBets() bool {
	msg := fmt.Sprintf("FIN|%s\n", c.config.ID)
	return c.sendWithAckRetry(msg, "fin")
}

// requestWinners solicita los ganadores al servidor, reintentando en caso de fallo
func (c *Client) requestWinners() {
	req := fmt.Sprintf("WINNERS|%s\n", c.config.ID)
	resp, ok := c.sendAndReadUntilPrefix(req, "WINNERS", "winners")

	if !ok {
		log.Errorf("action: consulta_ganadores | result: fail | client_id: %v", c.config.ID)
		return
	}

	dnis := bet.ParseWinnerResponse(resp)
	log.Infof("action: consulta_ganadores | result: success | cant_ganadores: %d", len(dnis))
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {
	signalsChannel := make(chan os.Signal, 1)
	signal.Notify(signalsChannel, os.Interrupt, syscall.SIGTERM)
	defer signal.Stop(signalsChannel)

	maxBatchSize := c.config.BatchMaxAmount
	if maxBatchSize <= 0 {
		maxBatchSize = DefaultBatchMaxAmount
	}

	parser, err := bet.NewParser(c.config.ID, maxBatchSize)
	if err != nil {
		log.Criticalf("action: open_csv | result: fail | error: %v", err)
		return
	}
	defer parser.Close()

	log.Infof("action: config | result: success | client_id: %v | server_address: %s | loop_amount: %d | loop_period: %v | log_level: INFO",
		c.config.ID, c.config.ServerAddress, c.config.LoopAmount, c.config.LoopPeriod)

	err = c.createClientSocket()
	if err != nil {
		log.Criticalf("client | action:connect | result:fail | client_id:%s | error:%v", c.config.ID, err)
		return
	}
	defer c.closeClientSocket()

	select {
	case <-signalsChannel:
		c.closeClientSocket()
		_ = parser.Close()
		log.Infof("action: client_shutdown | result: success | client_id: %v", c.config.ID)
		return

	default:
		c.sendBatchesFromParser(parser)
		c.notifyEndOfBets()
		c.requestWinners()
	}
	
	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}
