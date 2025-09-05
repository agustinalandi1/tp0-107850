package bet

import (
	"fmt"
	"strings"
	"unicode/utf8"
	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")
const maxMessageSize = 8192 // 8kB

type Bet struct {
	Nombre     string
	Apellido   string
	DNI       string
	Nacimiento string
	Numero     string
	Agencia    string
}

// serializeBet serializa los datos de una apuesta
func serializeBet(nombre, apellido, dni, nacimiento, numero, agencia string) string {
	fields := []string{nombre, apellido, dni, nacimiento, numero, agencia}
	msg := ""

	for i, field := range fields {
		msg += fmt.Sprintf("%d|%s", len(field), field)
		if i < len(fields)-1 {
			msg += "|" // separador entre campos, no al final
		}
	}

	return msg
}

// Verifica si la apuesta tiene todos los campos requeridos
func (b Bet) IsValid() bool {
	return b.Nombre != "" && b.Apellido != "" &&
		b.DNI != "" && b.Nacimiento != "" &&
		b.Numero != "" && b.Agencia != ""
}

// Serializa un batch de apuestas en un solo mensaje string listo para enviar
func SerializeBatch(batch []Bet) string {
	var parts []string
	for _, b := range batch {
		fields := []string{b.Nombre, b.Apellido, b.DNI, b.Nacimiento, b.Numero, b.Agencia}
		for _, field := range fields {
			parts = append(parts, fmt.Sprintf("%d|%s", utf8.RuneCountInString(field), field))
		}
	}
	return fmt.Sprintf("count|%d|%s\n", len(batch), strings.Join(parts, "|"))
}