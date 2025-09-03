# deserialize_bet deserializa los datos de una apuesta, devolviendo los campos individuales
def deserialize_bet(data: str):
    fields = []
    i = 0
    for _ in range(6):
        sep = data.find('|', i)
        if sep == -1:
            raise ValueError("invalid format: missing |")

        length_str = data[i:sep]
        try:
            length = int(length_str)
        except ValueError:
            raise ValueError(f"invalid length value: {length_str}")
        
        i = sep + 1
        value = data[i:i+length]
        if len(value) != length:
            raise ValueError("invalid format: length mismatch")

        fields.append(value)
        i += length

        if len(fields) < 6:
            if i >= len(data) or data[i] != '|':
                raise ValueError("invalid format: expected separator")
            i += 1

    nombre, apellido, dni, nacimiento, numero, agencia = fields
    return nombre, apellido, dni, nacimiento, numero, agencia

# Deserializa un mensaje de batch con formato: count|N|len|campo|len|campo|... (6 campos por apuesta)
# Devuelve una lista de apuestas como tuplas (nombre, apellido, dni, nacimiento, numero, agencia)
def deserialize_batch(data: str) -> list:
    
    parts = data.strip().split("|")
    if len(parts) < 2 or parts[0] != "count":
        raise ValueError("invalid format: missing count header")

    try:
        count = int(parts[1])
    except ValueError:
        raise ValueError("invalid count value")

    bets = []
    i = 2
    while len(bets) < count:
        fields = []
        for _ in range(6):
            if i + 1 >= len(parts):
                raise ValueError("invalid format: incomplete field")
            try:
                length = int(parts[i])
                value = parts[i + 1]
                if len(value) != length:
                    raise ValueError("length mismatch")
                fields.append(value)
                i += 2
            except Exception:
                raise ValueError("invalid field format")

        bets.append(tuple(fields))

    return bets
