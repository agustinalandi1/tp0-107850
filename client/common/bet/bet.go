package bet

import (
	"fmt"
	"os"
	"strings"
	
	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

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

	return msg + "\n"
}

func BuildBetMessage(agency string) (msg string, dni string, numero string) {
	nombre := strings.TrimSpace(os.Getenv("NOMBRE"))
	apellido := strings.TrimSpace(os.Getenv("APELLIDO"))
	dni = strings.TrimSpace(os.Getenv("DOCUMENTO"))
	nacimiento := strings.TrimSpace(os.Getenv("NACIMIENTO"))
	numero = strings.TrimSpace(os.Getenv("NUMERO"))
	agency = strings.TrimSpace(agency)

	log.Infof("DEBUG ENV nombre='%s' (%d) apellido='%s' dni='%s' nacimiento='%s' numero='%s' agencia='%s'",
		nombre, len(nombre), apellido, dni, nacimiento, numero, agency)

	msg = serializeBet(nombre, apellido, dni, nacimiento, numero, agency)
	log.Infof("DEBUG message: %s", msg)
	fmt.Printf("DEBUG serialized message:\n%s\n", msg)

	return msg, dni, numero
}
