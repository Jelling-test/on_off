import paho.mqtt.client as mqtt
import time
import sys
import logging
import json
import sqlite3
from datetime import datetime
import queue
import threading
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# MQTT Configuration
MQTT_BROKER = "192.168.0.208"
MQTT_PORT = 1883
MQTT_USER = "homeassistant"
MQTT_PASSWORD = "password123"
MQTT_KEEPALIVE = 60
MQTT_RECONNECT_DELAY = 5

# Globale variabler
message_queue = queue.Queue()
pending_readings = defaultdict(list)
BATCH_SIZE = 50
BATCH_TIMEOUT = 5  # sekunder

def get_meter_name(mac_address):
    """Hent måler navn fra database"""
    try:
        conn = sqlite3.connect('maaler_readings.db')
        cursor = conn.cursor()
        cursor.execute('SELECT meter_name FROM meters WHERE mac_address = ?', (mac_address,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        logging.error(f"Fejl ved opslag af måler navn: {str(e)}")
        return None

def save_readings_batch(readings):
    """Gem en batch af målinger"""
    try:
        conn = sqlite3.connect('maaler_readings.db')
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT INTO readings (ip_address, meter_name, total_energy, timestamp)
            VALUES (?, ?, ?, ?)
        ''', readings)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Fejl ved gemning af batch: {str(e)}")
        return False

def process_message_queue():
    """Behandl beskeder i batches for bedre performance"""
    while True:
        try:
            # Vent på at der er nok beskeder eller timeout
            start_time = time.time()
            while (len(pending_readings) < BATCH_SIZE and 
                   time.time() - start_time < BATCH_TIMEOUT):
                try:
                    # Få næste besked fra køen med timeout
                    msg = message_queue.get(timeout=1)
                    meter_id, data = msg
                    
                    # Konverter værdien til kWh
                    raw_value = data["ENERGY"]["ConsumptionTotal"]
                    kwh_value = float(raw_value) / 1000.0
                    
                    # Konverter tidspunkt
                    mqtt_time = datetime.strptime(data["Time"], "%Y-%m-%dT%H:%M:%S")
                    current_time = mqtt_time.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Find det rigtige måler navn baseret på meter_id
                    mac_address = meter_id[3:] if meter_id.startswith('obk') else meter_id
                    meter_name = get_meter_name(mac_address)
                    
                    if not meter_name:
                        logging.error(f"Ingen måler fundet med MAC adresse: {mac_address}")
                        continue
                    
                    # Tilføj til pending readings
                    pending_readings[meter_id].append((meter_id, meter_name, kwh_value, current_time))
                    
                    # Log målingen
                    energy_formatted = format(round(kwh_value, 2), '.2f').replace('.', ',')
                    logging.info(f"Måling klar til gemning for {meter_name}:")
                    logging.info(f"  Måler tidspunkt: {current_time}")
                    logging.info(f"  Konverteret til: {energy_formatted} kWh")
                    
                except queue.Empty:
                    continue
                    
            # Hvis der er beskeder at gemme
            if pending_readings:
                all_readings = []
                for meter_readings in pending_readings.values():
                    all_readings.extend(meter_readings)
                    
                if save_readings_batch(all_readings):
                    logging.info(f"Gemt batch med {len(all_readings)} målinger")
                else:
                    logging.error("Fejl ved gemning af batch")
                    
                # Ryd pending readings
                pending_readings.clear()
                
        except Exception as e:
            logging.error(f"Fejl i message queue processor: {str(e)}")
            time.sleep(1)  # Undgå CPU spild ved fejl

def on_disconnect(client, userdata, rc):
    logging.warning("Mistet forbindelse til MQTT broker med kode: %s", rc)
    if rc != 0:
        logging.info("Forsøger at genoprette forbindelse...")
        time.sleep(MQTT_RECONNECT_DELAY)
        try:
            client.reconnect()
        except Exception as e:
            logging.error(f"Fejl ved genoprettelse af forbindelse: {str(e)}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Forbundet til MQTT broker!")
        # Subscribe til alle relevante topics for den specifikke måler
        topics = [
            f"tele/obk{mac_suffix}/#" for mac_suffix in ["BFBFD7F0", "84E237"]
        ]
        for topic in topics:
            client.subscribe(topic)
            logging.info(f"Lytter på topic: {topic}")
    else:
        logging.error(f"Forbindelse fejlede med kode {rc}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode()
        
        # Log alle beskeder for at se hvad vi modtager
        logging.debug(f"Topic: {topic}")
        logging.debug(f"Payload: {payload}")
        
        # Prøv at parse JSON payload
        try:
            data = json.loads(payload)
            
            # Tjek om det er en SENSOR besked med ENERGY data
            if "ENERGY" in data and "Time" in data and "ConsumptionTotal" in data["ENERGY"]:
                # Udled meter_id fra topic (f.eks. tele/obkBFBFD7F0 -> obkBFBFD7F0)
                meter_id = topic.split('/')[1]
                
                # Tilføj til message queue i stedet for at gemme direkte
                message_queue.put((meter_id, data))
                    
        except json.JSONDecodeError:
            pass  # Ignorer ikke-JSON beskeder
            
    except Exception as e:
        logging.error(f"Fejl i message handler: {str(e)}")

def main():
    # Start message queue processor i en separat tråd
    processor_thread = threading.Thread(target=process_message_queue, daemon=True)
    processor_thread.start()
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            break
        except Exception as e:
            logging.error(f"Kunne ikke forbinde til MQTT broker: {str(e)}")
            time.sleep(MQTT_RECONNECT_DELAY)
    
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()
        sys.exit(0)

if __name__ == "__main__":
    main()
