import json
from pywebpush import Vapid01 # Importa la clase Vapid01
import sys # Importa el módulo sys para forzar la salida

print("Generando claves VAPID... Por favor, espera un momento.")
sys.stdout.flush() # Fuerza que este mensaje se muestre inmediatamente

try:
    # Crea una instancia de Vapid01
    vapid_instance = Vapid01()

    # Llama al método generate_keys() en la instancia
    vapid_keys = vapid_instance.generate_keys()

    # --- NUEVA LÍNEA DE DEPURACIÓN ---
    print(f"\nValor de 'vapid_keys' antes de JSON.dumps: {vapid_keys}")
    print(f"Tipo de 'vapid_keys': {type(vapid_keys)}\n")
    sys.stdout.flush() # Asegura que estos mensajes de depuración se muestren

    if vapid_keys: # Verifica si vapid_keys no es None o vacío
        print("\n¡Claves VAPID generadas con éxito!\n")
        print("--- INICIO DE CLAVES VAPID ---")
        print(json.dumps(vapid_keys, indent=4))
        print("--- FIN DE CLAVES VAPID ---\n")
        print("Por favor, copia la 'private_key' para tu app.py y la 'public_key' para tus archivos HTML.")
    else:
        print("\nAdvertencia: La función generate_keys() no devolvió claves VAPID válidas.")
        print("Esto puede indicar un problema con la librería 'pywebpush' en tu entorno.")

except Exception as e:
    print(f"\n¡Ocurrió un error al generar las claves VAPID: {e}")
    print("Asegúrate de que 'pywebpush' esté correctamente instalado en tu entorno virtual.")

sys.stdout.flush() # Asegura que toda la salida se muestre