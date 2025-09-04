package communication

import (
	"errors"
	"io"
	"net"
	"bufio"
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

// ReceiveAck lee exactamente 3 bytes: "OK\n"
func ReceiveAck(conn net.Conn) error {
	buf := make([]byte, 3)
	_, err := io.ReadFull(conn, buf)
	if err != nil {
		return err
	}
	if string(buf) != "OK\n" {
		return errors.New("ack not OK")
	}
	return nil
}

// ReadMessage lee una respuesta de texto completa del servidor
func ReadMessage(conn net.Conn) (string, error) {
	reader := bufio.NewReader(conn)
	response, err := reader.ReadString('\n')
	if err != nil {
		return "", err
	}
	return response[:len(response)-1], nil // para sacar el '\n'
}