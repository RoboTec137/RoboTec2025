import socket
import threading
import time
import pygame
#from adafruit_servokit import ServoKit
#import RPi.GPIO as GPIO

target_ip = "192.168.0.209"
MI_IP = "192.168.0.105"

UDP_IP = "0.0.0.0"
UDP_PORT = 5005
TIMEOUT = 1
MAX_RETRIES = 5

pending_acks = {}
ack_lock = threading.Lock()
sequence_counter = 1
sequence_lock = threading.Lock()
pygame.mixer.init()

#kit = ServoKit(channels=16)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.settimeout(1)

BUTTON_PIN = 17
#GPIO.setmode(GPIO.BCM)
#GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down= GPIO.PUD_UP)

print("Servidor UDP en ejecución en el puerto", UDP_PORT)

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
    "linea_1": "Nos espera un gran camino Don quijote.", 
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

ROL = "sancho"

sync_done = False

def get_next_sequence():
    global sequence_counter
    with sequence_lock:
        seq = sequence_counter
        sequence_counter += 1
        return seq

def process_command(message, addr):
    global sync_done
    print("Ejecutando process_command con:", repr(message))
    if message.lower().startswith("servo"):
        parts = message.split()
        if len(parts) >= 3:
            try:
                canal = int(parts[1])
                angulo = int(parts[2])
                #kit.servo[canal].angle = angulo
                print(f"Moviendo servo en canal {canal} a {angulo}°")
                confirmation = f"Servo {canal} movido a {angulo}°"
                sock.sendto(confirmation.encode(), addr)
            except Exception as e:
                print("Error al mover el servo:", e)
        else:
            print("Comando de servo mal formateado. Uso: servo <canal> <ángulo>")

    elif message.lower().strip() == "ping":
        response = "pong"
        sock.sendto(response.encode(), addr)
        print(f"Recibido 'ping' de {addr}. Respondido con 'pong'.")
    elif message.lower() == "pong":
        print(f"Recibido 'pong' de {addr}")
    
    elif message.lower() == "HANDSHAKE_INICIO":
        sync_done = True
        print("Comando 'inicio' recibido para sincronización.")
        iniciar_conversacion()
        handshake_sync()

    else:
        print("Mensaje recibido (sin comando especial):", message)

def listener():
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            mensaje = data.decode()
            if mensaje.startswith("ACK:"):
                try:
                    seq = int(mensaje.split(":", 1)[1])
                    with ack_lock:
                        if seq in pending_acks:
                            print(f"Recibido ACK para secuencia {seq} desde {addr}")
                            pending_acks[seq].set()
                except ValueError:
                    print("Formato de ACK incorrecto")
            else:
                if ":" in mensaje:
                    seq_str, actual_message = mensaje.split(":", 1)
                    try:
                        seq = int(seq_str)
                    except ValueError:
                        seq = None
                    print(f"Recibido mensaje de {addr}: {actual_message} (Secuencia: {seq})")
                    if seq is not None:
                        ack_msg = f"ACK:{seq}"
                        sock.sendto(ack_msg.encode(), addr)
                        print(f"Enviado {ack_msg} a {addr}")
                    process_command(actual_message, addr)
                else:
                    print(f"Mensaje con formato inesperado: {mensaje}")
                    
        except socket.timeout:
            continue
      
def sender():
    while True:
        message = input("Ingresa el mensaje: ").strip()
        seq = get_next_sequence()
        packet = f"{seq}:{message}"
        attempt = 0
        ack_received = False
        
        event = threading.Event()
        with ack_lock:
            pending_acks[seq] = event
            
        while attempt < MAX_RETRIES and not ack_received:
            print(f"Enviando (intento {attempt+1}) a {target_ip}: {packet}")
            sock.sendto(packet.encode(), (target_ip, UDP_PORT))
            ack_received = event.wait(TIMEOUT)
            if not ack_received:
                attempt += 1
                print("No se recibió ACK, reintentando...")
                
        if ack_received:
            print("Mensaje entregado exitosamente!")
        else:
            print("Error: No se recibió ACK después de  múltiples intentos.")
            
        with ack_lock:
            
            if seq in pending_acks:
                del pending_acks[seq]

def button_callback():
    print("Botón físico presionado!")
    message = "mensaje enviado desde el botón físico"
    seq = get_next_sequence()
    packet = f"{seq}:{message}"
    attempt = 0
    ack_received = False

    event = threading.Event()
    with ack_lock:
        pending_acks[seq] = event

    while attempt < MAX_RETRIES and not ack_received:
        print(f"Enviando (intento {attempt+1}) desde botón a {target_ip}: {packet}")
        sock.sendto(packet.encode(), (target_ip, UDP_PORT))
        if not ack_received:
            attempt += 1
            print("No se recibió ACK, reintentando mensaje del botón...")

    if ack_received:    
        print("Mensaje del botón entregado exitosamente!")

    else:
        print("Error: No se recibió ACK para el mensaje del botón")

    with ack_lock:
        if seq in pending_acks:
            del pending_acks[seq]


def reproducir_audio(file_path):
    try:
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print("Error reproduciendo audio:", e)

def enviar_linea(linea):
    sock.sendto(linea.encode(), (target_ip, UDP_PORT))
    print(f"Enviado: {linea}")

def enviar_y_reproducir(linea, audio_file):
    hilo_audio = threading.Thread(target=reproducir_audio, args=(audio_file,))
    hilo_audio.start()
    enviar_linea(linea)
    hilo_audio.join()

def reproducir_audio_secuencia(audio_files):
    for file in audio_files:
        reproducir_audio(file)
        time.sleep(0.1)

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
        for idx, linea in enumerate(grupo):
            if int(linea.split('_')[1]) <= 3:
                audio_files.append(f"audio_dq_real_{linea}.mp3")
            else:
                audio_files.append(f"audio_dq_{linea}.mp3")
        print("\nDon Quijote dice:")
        enviar_y_reproducir(texto, audio_files)
        time.sleep(1)
        try:
            data, addr = sock.recvfrom(1024)
            print("Respuesta de Sancho Panza:", data.decode())
        except socket.timeout:
            print("No se recibió respuesta de Sancho Panza.")
        time.sleep(0.5)

def conversacion_sancho_panza_grupos():
    grupos = [
        ["linea_1"], ["linea_2"], ["linea_3"],
        ["linea_4", "linea_5"],
        ["linea_6", "linea_7", "linea_8"],
        ["linea_9", "linea_10"],
    ]
    for grupo in grupos:
        try:
            data, addr = sock.recvfrom(1024)
            print("Don Quijote dijo:", data.decode())
        except socket.timeout:
            print("No se recibió mensaje de Don Quijote.")
        time.sleep(0.5)
        texto = " ".join(guion_sancho_panza[linea] for linea in grupo if linea in guion_sancho_panza)
        audio_files = [f"audio_sp_{linea}.mp3" for linea in grupo]
        print("\nSancho Panza responde:")
        enviar_y_reproducir(texto, audio_files)
        time.sleep(1)

sync_done = False

def handshake_sync():
    global sync_done
    print("Iniciando handshake de sincronización...")
    enviar_linea("HANDSHAKE_INICIO")
    timeout = 10
    start = time.time()
    while not sync_done:
        if time.time() - start > timeout:
            print("Timeout en handshake, reenviando 'inicio'...")
            enviar_linea("HANDSHAKE_INICIO")
            start = time.time()
        time.sleep(0.1)
    print("Handshaking completado. ¡Sincronizados!")

def iniciar_conversacion():
    if ROL == "don":
        conversacion_don_quijote_grupos()
    else:
        conversacion_sancho_panza_grupos()

#GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback= button_callback, bouncetime= 300)

hilo_receptor = threading.Thread(target= listener, daemon= True)
hilo_emisor = threading.Thread(target= sender, daemon= True)

hilo_receptor.start()
hilo_emisor.start()

hilo_receptor.join()
hilo_emisor.join()
