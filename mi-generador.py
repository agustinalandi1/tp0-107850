import yaml
import sys

def generar_docker_compose(archivo_salida, cantidad_clientes):
    data = {
        'services': {
            'server': {
                'container_name': 'server',
                'image': 'server:latest',
                'entrypoint': 'python3 /main.py',
                'environment': [
                    'PYTHONUNBUFFERED=1',
                    'LOGGING_LEVEL=DEBUG'
                ],
                'networks': ['testing_net']
            }
        },
        'networks': {
            'testing_net': {
                'ipam': {
                    'driver': 'default',
                    'config': [
                        {'subnet': '172.25.125.0/24'}
                    ]
                }
            }
        }
    }

    for i in range(1, cantidad_clientes + 1):
        nombre = f'client{i}'
        data['services'][nombre] = {
            'container_name': nombre,
            'image': 'client:latest',
            'entrypoint': '/client',
            'environment': [
                f'CLI_ID={i}',
                'CLI_LOG_LEVEL=DEBUG'
            ],
            'networks': ['testing_net'],
            'depends_on': ['server']
        }

    with open(archivo_salida, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

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
