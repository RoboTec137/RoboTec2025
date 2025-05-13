import socket
import threading
import time
import pygame
#from adafruit_servokit import ServoKit
#import RPi.GPIO as GPIO
import queue

# CONFIGURACIÓN DE RED Y HARDWARE
# Configura las IPs:
# En el dispositivo de Don Quijote:
#     MI_IP = "192.168.0.105"
#     TARGET_IP = "192.168.0.106"
# En el dispositivo de Sancho Panza:
#     MI_IP = "192.168.0.106"
#     TARGET_IP = "192.168.0.105"
MI_IP = "192.168.0.209"      # Cambia según dispositivo
TARGET_IP = "192.168.0.105"  # IP del otro dispositivo

UDP_IP = "0.0.0.0"
UDP_PORT = 5005
TIMEOUT = 1
MAX_RETRIES = 5

# Variables globales para ACK y secuencias
pending_acks = {}
ack_lock = threading.Lock()
sequence_counter = 1
sequence_lock = threading.Lock()

# Inicialización de pygame y servo (si aplica)
pygame.mixer.init()
#kit = ServoKit(channels=16)

# Configurar socket UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((MI_IP, UDP_PORT))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.settimeout(1)

# Configuración de GPIO (si se requiere)
BUTTON_PIN = 17
#GPIO.setmode(GPIO.BCM)
#GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Servidor UDP en ejecución en el puerto", UDP_PORT)

# GUIONES
guion_don_quijote = {
    "linea_1": "sí, como ninguna otra", 
    "linea_2": "Gracias.", 
    "linea_3": "Sancho, prepárate para pelear contra los gigantes de muchos brazos.", 
    "linea_4": "tra-la-la-la-la",
    "linea_5": "No permitas que deje de brillar",
    "linea_6": "Pues mis sueños vas a derrumbar",
    "linea_7": "Mira Sancho, más allá",
    "linea_8": "Son gigantes que te tengo que acabar.",
    "linea_9": "Mira Sancho esta vez",
    "linea_10": "Ahora no voy a retroceder",
    "linea_11": "Pues los malos van a arder",
    "linea_12": "Con mi espada voy a rebanar",
    "linea_13": "Cada parte de su andar.",
    "linea_14": "¡Ay Sancho! ¡Deja de molestar!",
    "linea_15": "Pues con mi triunfo vas a acabar",
    "linea_16": "¡Ay Sancho! No te faltó razón",
    "linea_17": "Porque no sé, a qué camino voy",
}

guion_sancho_panza = {
    "linea_1": "Nos espera un gran camino, Don Quijote.", 
    "linea_2": "No son gigantes.", 
    "linea_3": "¿Por qué comienzas a cantar?", 
    "linea_4": "¿Acaso son los libros de nuevo que comienzas a idealizar?",
    "linea_5": "Y si sigues así, pues tu realidad por completo se va a alterar…",
    "linea_6": "¿Y NO ME DEJAS TERMINAR?",
    "linea_7": "Entra ya en razón",
    "linea_8": "Porque la caballería no es tu don",
    "linea_9": "Noo su majestad, ¡Esas páginas te tienen mal!",
    "linea_10": "Y a este ataque no te voy acompañar",
}

# DEFINICIÓN DEL ROL
# En el dispositivo de Don Quijote: ROL = "don"
# En el dispositivo de Sancho Panza: ROL = "sancho"
ROL = "don"  # Cambia según corresponda

# Variable y cola para sincronización
handshake_event = threading.Event()
message_queue = queue.Queue()

# HILO LISTENER: Lee continuamente mensajes y los pone en la cola
def listener():
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            mensaje = data.decode().strip()
            print(f"[Listener] Recibido de {addr}: {mensaje}")
            message_queue.put((mensaje, addr))
        except socket.timeout:
            continue

# FUNCIONES DE AUDIO Y ENVÍO
def reproducir_audio(file_path):
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print("Error reproduciendo audio:", e)

def enviar_linea(linea):
    sock.sendto(linea.encode(), (TARGET_IP, UDP_PORT))
    print(f"[Envío] {linea}")

def enviar_y_reproducir(linea, audio_files):
    hilo_audio = threading.Thread(target=reproducir_audio_secuencia, args=(audio_files,))
    hilo_audio.start()
    enviar_linea(linea)
    hilo_audio.join()

def reproducir_audio_secuencia(audio_files):
    for file in audio_files:
        reproducir_audio(file)
        time.sleep(0.1)

def get_next_sequence():
    global sequence_counter
    with sequence_lock:
        seq = sequence_counter
        sequence_counter += 1
        return seq

# HANDSHAKE: Envía y espera el comando de sincronización
def handshake_sync():
    print("Iniciando handshake de sincronización...")
    # Envía el mensaje de handshake
    enviar_linea("HANDSHAKE_INICIO")
    # Espera hasta recibirlo del otro dispositivo
    try:
        mensaje, addr = message_queue.get(timeout=10)
        if mensaje.upper() == "HANDSHAKE_INICIO":
            print("Handshake recibido desde", addr)
            handshake_event.set()
    except queue.Empty:
        print("Timeout en handshake. Reintentando...")
        handshake_sync()  # Reintento recursivo (cuidado con recursión excesiva)

# CONVERSACIÓN AGRUPADA

def conversacion_don_quijote_grupos():
    grupos = [
        ["linea_1"], ["linea_2"], ["linea_3"], ["linea_4"],
        ["linea_5", "linea_6"],
        ["linea_7", "linea_8"],
        ["linea_9", "linea_10", "linea_11", "linea_12", "linea_13"],
        ["linea_14", "linea_15"],
        ["linea_16", "linea_17"],
    ]
    for grupo in grupos:
        texto = " ".join(guion_don_quijote[linea] for linea in grupo if linea in guion_don_quijote)
        audio_files = []
        for linea in grupo:
            if int(linea.split('_')[1]) <= 3:
                audio_files.append(f"audio_dq_real_{linea}.mp3")
            else:
                audio_files.append(f"audio_dq_{linea}.mp3")
        print("\n[Don Quijote] Dice:")
        enviar_y_reproducir(texto, audio_files)
        time.sleep(1)
        # Espera respuesta de Sancho
        try:
            mensaje, addr = message_queue.get(timeout=5)
            print("[Don Quijote] Recibió respuesta:", mensaje)
        except queue.Empty:
            print("[Don Quijote] No se recibió respuesta de Sancho.")
        time.sleep(0.5)

def conversacion_sancho_panza_grupos():
    grupos = [
        ["linea_1"], ["linea_2"], ["linea_3"],
        ["linea_4", "linea_5"],
        ["linea_6", "linea_7", "linea_8"],
        ["linea_9", "linea_10"],
    ]
    for grupo in grupos:
        # Espera mensaje de Don Quijote
        try:
            mensaje, addr = message_queue.get(timeout=5)
            print("[Sancho] Don Quijote dijo:", mensaje)
        except queue.Empty:
            print("[Sancho] No se recibió mensaje de Don Quijote.")
        time.sleep(0.5)
        texto = " ".join(guion_sancho_panza[linea] for linea in grupo if linea in guion_sancho_panza)
        audio_files = [f"audio_sp_{linea}.mp3" for linea in grupo]
        print("\n[Sancho] Responde:")
        enviar_y_reproducir(texto, audio_files)
        time.sleep(1)

def iniciar_conversacion():
    if ROL == "don":
        conversacion_don_quijote_grupos()
    else:
        conversacion_sancho_panza_grupos()

# OTRA FUNCIONALIDAD: sender (para comandos manuales)
def sender():
    while True:
        message = input("Ingresa el mensaje: ").strip()
        seq = get_next_sequence()
        packet = f"{seq}:{message}"
        sock.sendto(packet.encode(), (TARGET_IP, UDP_PORT))
        print(f"[Manual] Enviado: {packet}")

# Hilo de sender (opcional, para comandos manuales)
hilo_sender = threading.Thread(target=sender, daemon=True)

# Iniciar el hilo listener
hilo_listener = threading.Thread(target=listener, daemon=True)
hilo_listener.start()
hilo_sender.start()

# HANDSHAKE: ambos dispositivos deben enviar y recibir "HANDSHAKE_INICIO"
handshake_sync()
# Espera a que ambos se sincronicen
if handshake_event.is_set():
    print("Dispositivos sincronizados, iniciando conversación...")
    iniciar_conversacion()
else:
    print("Error en la sincronización.")

hilo_listener.join()
hilo_sender.join()
