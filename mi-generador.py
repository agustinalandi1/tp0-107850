import sys

def generar_docker_compose(archivo_salida, cantidad_clientes):
    compose = """name: tp0
services:
  server:
    container_name: server
    image: server:latest
    entrypoint: python3 /main.py
    environment:
      - PYTHONUNBUFFERED=1
      - LOGGING_LEVEL=DEBUG
    networks:
      - testing_net
    volumes:
      - ./server/config.ini:/config.ini
"""

    # Clientes
    for i in range(1, cantidad_clientes + 1):
        compose += f"""  client{i}:
    container_name: client{i}
    image: client:latest
    entrypoint: /client
    environment:
      - CLI_ID={i}
      - CLI_LOG_LEVEL=DEBUG
    networks:
      - testing_net
    volumes:
      - ./client/config.yaml:/config.yaml
    depends_on:
      - server
"""

    # Red
    compose += """networks:
  testing_net:
    ipam:
      driver: default
      config:
        - subnet: 172.25.125.0/24
"""

    with open(archivo_salida, 'w') as f:
        f.write(compose)

    print(f"Docker Compose file '{archivo_salida}' generado con {cantidad_clientes} cliente(s).")

if __name__ == '__main__':
    #if len(sys.argv) != 3:
    #    print('Uso: python3 mi-generador.py <archivo_salida> <cantidad_clientes>')
    #    sys.exit(1)

    archivo = sys.argv[1]
    
    try:
        cantidad = int(sys.argv[2])
        if cantidad < 1:
            raise ValueError
    except ValueError:
        print("Error: la cantidad de clientes debe ser un número entero positivo.")
        sys.exit(1)

    generar_docker_compose(archivo, cantidad)
    print(f"Archivo '{archivo}' generado con {cantidad} cliente(s).")
