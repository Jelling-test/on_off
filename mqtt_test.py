import paho.mqtt.client as mqtt
import time
import sys
import logging
import json
import mysql.connector
from datetime import datetime
import queue
import threading
from collections import defaultdict
import re

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# MQTT Configuration
MQTT_BROKER = "192.168.9.61"
MQTT_PORT = 1890
MQTT_USER = "homeassistant"
MQTT_PASSWORD = "password123"
MQTT_KEEPALIVE = 60
MQTT_RECONNECT_DELAY = 5

# Database Configuration
DB_CONFIG = {
    'host': '192.168.9.61',
    'port': 3306,
    'user': 'homeassistant',
    'password': 'da7vu.so-2TEi67U81',
    'database': 'maaler_laes'
}

# Globale variabler
message_queue = queue.Queue()
pending_readings = defaultdict(list)
BATCH_SIZE = 50
BATCH_TIMEOUT = 5  # sekunder

def get_meter_name(mac_address):
    """Hent måler navn fra database"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Prøv først med den fulde MAC adresse
        cursor.execute('SELECT meter_name FROM meters WHERE mac_address LIKE %s LIMIT 1', (f'%{mac_address}%',))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result['meter_name'] if result else None
        
    except Exception as e:
        logging.error(f"Database fejl i get_meter_name: {str(e)}")
        return None

def save_readings_batch(readings):
    """Gem en batch af målinger"""
    if not readings:
        return
        
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        insert_query = '''
        INSERT INTO readings (ip_address, meter_name, total_energy, timestamp)
        VALUES (%s, %s, %s, %s)
        '''
        
        cursor.executemany(insert_query, readings)
        conn.commit()
        
        cursor.close()
        conn.close()
        
        logging.info(f"Gemt {len(readings)} målinger i databasen")
        
    except Exception as e:
        logging.error(f"Database fejl i save_readings_batch: {str(e)}")

def process_message_queue():
    """Behandl beskeder i batches for bedre performance"""
    global pending_readings
    last_save_time = time.time()
    
    while True:
        try:
            # Vent på næste besked med timeout
            try:
                msg = message_queue.get(timeout=1)
                topic = msg.topic
                payload = msg.payload.decode()
                
                # Log alle beskeder for at se hvad vi modtager
                logging.debug(f"Topic: {topic}")
                logging.debug(f"Payload: {payload}")
                
                try:
                    data = json.loads(payload)
                    
                    # Tjek om det er en SENSOR besked med ENERGY data
                    if "ENERGY" in data and "Time" in data and "ConsumptionTotal" in data["ENERGY"]:
                        # Udled meter_id fra topic (f.eks. tele/obkBFBFD7F0 -> BFBFD7F0)
                        meter_id = topic.split('/')[1]
                        mac_address = meter_id[3:] if meter_id.startswith('obk') else meter_id
                        meter_name = get_meter_name(mac_address)
                        
                        if not meter_name:
                            logging.error(f"Ingen måler fundet med MAC adresse: {mac_address}")
                            continue
                            
                        # Konverter værdien til kWh
                        raw_value = data["ENERGY"]["ConsumptionTotal"]
                        kwh_value = float(raw_value)
                        
                        # Konverter tidspunkt
                        mqtt_time = datetime.strptime(data["Time"], "%Y-%m-%dT%H:%M:%S")
                        current_time = mqtt_time.strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Gem måling i pending listen med None som ip_address
                        reading = (None, meter_name, kwh_value, current_time)
                        pending_readings[meter_name].append(reading)
                        
                        # Log målingen
                        energy_formatted = format(round(kwh_value, 2), '.2f').replace('.', ',')
                        logging.info(f"Måling klar til gemning for {meter_name}:")
                        logging.info(f"  Måler tidspunkt: {current_time}")
                        logging.info(f"  Total energi: {energy_formatted} kWh")
                        
                except json.JSONDecodeError:
                    logging.error(f"Ugyldig JSON i besked: {payload}")
                except Exception as e:
                    logging.error(f"Fejl ved behandling af besked: {str(e)}")
                    
            except queue.Empty:
                pass
                
            # Gem målinger hvis vi har nok eller der er gået for lang tid
            current_time = time.time()
            total_readings = sum(len(readings) for readings in pending_readings.values())
            
            if (total_readings >= BATCH_SIZE or 
                (current_time - last_save_time >= BATCH_TIMEOUT and total_readings > 0)):
                
                # Saml alle målinger til én liste
                all_readings = []
                for meter_readings in pending_readings.values():
                    all_readings.extend(meter_readings)
                
                # Gem målinger og nulstil pending
                save_readings_batch(all_readings)
                pending_readings.clear()
                last_save_time = current_time
                
        except Exception as e:
            logging.error(f"Fejl i process_message_queue: {str(e)}")
            time.sleep(1)

def on_disconnect(client, userdata, rc):
    logging.warning("Mistet forbindelse til MQTT broker med kode: %s", rc)
    while True:
        try:
            if client.reconnect() == 0:
                logging.info("Genoprettet forbindelse til MQTT broker")
                break
        except Exception:
            pass
        time.sleep(MQTT_RECONNECT_DELAY)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Forbundet til MQTT broker!")
        # Subscribe til alle relevante topics for den specifikke måler
        topics = [
            f"tele/obk{mac_suffix}/SENSOR" for mac_suffix in ["BFBFD7F0", "84E237"]
        ]
        for topic in topics:
            client.subscribe(topic)
            logging.info(f"Lytter på topic: {topic}")
    else:
        logging.error(f"Forbindelse fejlede med kode {rc}")

def on_message(client, userdata, msg):
    try:
        # Put message in queue for processing
        message_queue.put(msg)
    except Exception as e:
        logging.error(f"Fejl i message handler: {str(e)}")

def main():
    # Start message processing thread
    process_thread = threading.Thread(target=process_message_queue, daemon=True)
    process_thread.start()
    
    # Set up MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    # Set MQTT authentication
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    
    # Connect to broker
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            break
        except Exception as e:
            logging.error(f"Kunne ikke forbinde til MQTT broker: {str(e)}")
            time.sleep(MQTT_RECONNECT_DELAY)
    
    # Start MQTT loop
    client.loop_forever()

if __name__ == "__main__":
    main()
