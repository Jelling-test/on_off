import sqlite3
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import logging
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

class AlertManager:
    def __init__(self, db_path, email_config):
        self.db_path = db_path
        self.email_config = email_config
        self.last_alert_sent = {}  # Hold styr på hvornår der sidst er sendt alert for hver måler
    
    def check_offline_meters(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Hent seneste måling for hver måler
            cursor.execute('''
                SELECT meter_name, MAX(timestamp), total_energy
                FROM readings
                GROUP BY meter_name
            ''')
            
            results = cursor.fetchall()
            current_time = datetime.now()
            
            for meter_name, last_reading_time, last_energy in results:
                last_reading_dt = datetime.strptime(last_reading_time, '%Y-%m-%d %H:%M:%S')
                time_difference = current_time - last_reading_dt
                
                # Hvis måler har været offline i mere end 4 timer og der ikke er sendt alert inden for de sidste 24 timer
                if time_difference > timedelta(hours=4):
                    last_alert = self.last_alert_sent.get(meter_name)
                    if not last_alert or (current_time - last_alert) > timedelta(hours=24):
                        self.send_alert_email(meter_name, last_reading_time, last_energy)
                        self.last_alert_sent[meter_name] = current_time
            
            conn.close()
            
        except Exception as e:
            logging.error(f"Fejl ved tjek af offline målere: {str(e)}")
    
    def send_alert_email(self, meter_name, last_reading_time, last_energy):
        try:
            subject = "Måler offline"
            
            # Formater energi med komma og 2 decimaler
            energy_formatted = format(round(float(last_energy), 2), '.2f').replace('.', ',')
            
            body = f"""
Måler nummer: {meter_name}
Sidste aflæsning: {energy_formatted} kWh
Offline kl.: {last_reading_time}
            """
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.email_config['from_email']
            msg['To'] = self.email_config['to_email']
            
            # Send email via SMTP
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)
            
            logging.info(f"Alert email sendt for {meter_name}")
            
        except Exception as e:
            logging.error(f"Fejl ved afsendelse af email: {str(e)}")

def start_alert_monitor():
    # Email konfiguration
    email_config = {
        'smtp_server': 'smtp.gmail.com',  # Erstat med din SMTP server
        'smtp_port': 587,
        'username': 'your_email@gmail.com',  # Erstat med din email
        'password': 'your_password',  # Erstat med din adgangskode
        'from_email': 'your_email@gmail.com',  # Erstat med afsender email
        'to_email': 'peter@jellingcamping.dk'
    }
    
    alert_manager = AlertManager('maaler_readings.db', email_config)
    
    while True:
        alert_manager.check_offline_meters()
        time.sleep(300)  # Tjek hver 5. minut

if __name__ == "__main__":
    start_alert_monitor()
