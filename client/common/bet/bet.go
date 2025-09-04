package bet

import (
	"fmt"
	"os"
	"encoding/csv"
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

// Lee el archivo CSV y arma un slice de apuestas
func ReadCSV(path, agencyID string) ([]Bet, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("error opening CSV file: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("error reading CSV: %w", err)
	}

	var bets []Bet
	for _, record := range records {
		if len(record) != 5 {
			continue
		}
		bets = append(bets, Bet{
			Nombre:     strings.TrimSpace(record[0]),
			Apellido:   strings.TrimSpace(record[1]),
			DNI:        strings.TrimSpace(record[2]),
			Nacimiento: strings.TrimSpace(record[3]),
			Numero:     strings.TrimSpace(record[4]),
			Agencia:    agencyID,
		})
	}

	return bets, nil
}

// Divide el slice de apuestas en sub-slices de tamaño máximo maxAmount
func SplitInBatches(bets []Bet, maxAmount int) [][]Bet {
	var batches [][]Bet
	for i := 0; i < len(bets); i += maxAmount {
		end := i + maxAmount
		if end > len(bets) {
			end = len(bets)
		}
		batches = append(batches, bets[i:end])
	}
	return batches
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


// Función principal que crea el mensaje final, dividiendo en batches si es necesario
func BuildBatchMessages(agencyID string, maxAmount int) ([]string, error) {
	path := fmt.Sprintf("/data/agency-%s.csv", agencyID)
	bets, err := ReadCSV(path, agencyID)
	if err != nil {
		return nil, err
	}

	rawBatches := SplitInBatches(bets, maxAmount)
	var messages []string

	for i, batch := range rawBatches {
		serialized := SerializeBatch(batch)

		if len(serialized) > maxMessageSize {
			fmt.Printf("WARNING: batch %d skipped (size %d > 8kB)\n", i, len(serialized))
			continue
		}

		messages = append(messages, serialized)
	}

	fmt.Printf("DEBUG: total valid bets: %d, total batches: %d\n", len(bets), len(messages))
	return messages, nil
}