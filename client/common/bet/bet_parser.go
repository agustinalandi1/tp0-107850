package bet

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"strings"
)

const maxMessageSize = 8192 // 8kB

type Parser struct {
	file     *os.File
	reader   *csv.Reader
	agencyID string
	maxBatch int
}

// Inicializa el parser con la agencia y tamaño de batch
func NewParser(agencyID string, maxBatch int) (*Parser, error) {
	path := fmt.Sprintf("/data/agency-%s.csv", agencyID)
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}

	reader := csv.NewReader(bufio.NewReader(f))
	return &Parser{
		file:     f,
		reader:   reader,
		agencyID: agencyID,
		maxBatch: maxBatch,
	}, nil
}

// Cierra el archivo CSV
func (p *Parser) Close() error {
	return p.file.Close()
}

// Lee el próximo batch válido (por cantidad o tamaño)
func (p *Parser) NextBatch() ([]Bet, error) {
	var bets []Bet
	count := 0
	totalSize := 0

	for count < p.maxBatch {
		record, err := p.reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil || len(record) != 5 {
			continue // línea inválida
		}

		b := Bet{
			Nombre:     strings.TrimSpace(record[0]),
			Apellido:   strings.TrimSpace(record[1]),
			DNI:        strings.TrimSpace(record[2]),
			Nacimiento: strings.TrimSpace(record[3]),
			Numero:     strings.TrimSpace(record[4]),
			Agencia:    p.agencyID,
		}
		if !b.IsValid() {
			continue
		}

		nextSize := totalSize + len(serializeBet(
			b.Nombre, b.Apellido, b.DNI, b.Nacimiento, b.Numero, b.Agencia,
		))
		if nextSize > maxMessageSize {
			break
		}

		bets = append(bets, b)
		totalSize = nextSize
		count++
	}

	if count == 0 {
		return nil, io.EOF
	}

	return bets, nil
}
