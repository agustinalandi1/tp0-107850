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
