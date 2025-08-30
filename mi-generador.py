import yaml
import sys

def generar_docker_compose(archivo_salida, cantidad_clientes):
    with open(archivo_salida, 'w') as f:

        f.write("name: tp0\n")
        f.write("services:\n")
        
        # Servidor
        f.write("  server:\n")
        f.write("    container_name: server\n")
        f.write("    image: server:latest\n")
        f.write("    entrypoint: python3 /main.py\n")
        f.write("    environment:\n")
        f.write("      - PYTHONUNBUFFERED=1\n")
        f.write("      - LOGGING_LEVEL=DEBUG\n")
        f.write("    networks:\n")
        f.write("      - testing_net\n")

        # Clientes
        for i in range(1, cantidad_clientes + 1):
            f.write(f"  client{i}:\n")
            f.write(f"    container_name: client{i}\n")
            f.write(f"    image: client:latest\n")
            f.write(f"    entrypoint: /client\n")
            f.write(f"    environment:\n")
            f.write(f"      - CLI_ID={i}\n")
            f.write(f"      - CLI_LOG_LEVEL=DEBUG\n")
            f.write(f"    networks:\n")
            f.write(f"      - testing_net\n")
            f.write(f"    depends_on:\n")
            f.write(f"      - server\n")

        # Red
        f.write("networks:\n")
        f.write("  testing_net:\n")
        f.write("    ipam:\n")
        f.write("      driver: default\n")
        f.write("      config:\n")
        f.write("        - subnet: 172.25.125.0/24\n")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Uso: python3 mi-generador.py <archivo_salida> <cantidad_clientes>')
        sys.exit(1)

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
