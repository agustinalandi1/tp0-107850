#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Nombre del archivo de salida: $1"
echo "Cantidad de clientes: $2"
echo "Ruta del generador: $SCRIPT_DIR/mi-generador.py"

python3 "$SCRIPT_DIR/mi-generador.py" "$1" "$2"
