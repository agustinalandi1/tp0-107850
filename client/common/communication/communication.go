package communication

import (
	"errors"
	"io"
	"net"
)

// SendMessage escribe el mensaje y lo envia
func SendMessage(conn net.Conn, message string) error {
	total := 0
	data := []byte(message)

	for total < len(data) {
		n, err := conn.Write(data[total:])
		if err != nil {
			return err
		}
		total += n
	}
	return nil
}

// ReceiveAck lee exactamente 2 bytes: "OK"
func ReceiveAck(conn net.Conn) error {
	buf := make([]byte, 2)
	_, err := io.ReadFull(conn, buf)
	if err != nil {
		return err
	}
	if string(buf) != "OK" {
		return errors.New("ack not OK")
	}
	return nil
}
