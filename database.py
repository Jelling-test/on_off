import mysql.connector
from datetime import datetime, timedelta
import logging

class MaalerDatabase:
    def __init__(self):
        self.db_config = {
            'host': '192.168.9.61',
            'port': 3306,
            'user': 'homeassistant',
            'password': 'da7vu.so-2TEi67U81',
            'database': 'maaler_laes'
        }
        self._init_db()
        
    def _get_connection(self):
        return mysql.connector.connect(**self.db_config)
        
    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Opret tabel til målinger hvis den ikke findes
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ip_address VARCHAR(255),
            meter_name VARCHAR(255),
            total_energy FLOAT,
            timestamp DATETIME,
            mac_address VARCHAR(255)
        )
        ''')

        # Opret tabel til måler-konfiguration med kun MAC adresse som unik
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meters (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ip_address VARCHAR(255),
            meter_name VARCHAR(255),
            mac_address VARCHAR(255) UNIQUE,
            created_at DATETIME
        )
        ''')

        # Opret tabel til målergrupper
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meter_groups (
            id INT AUTO_INCREMENT PRIMARY KEY,
            group_name VARCHAR(255) UNIQUE,
            created_at DATETIME
        )
        ''')

        # Opret tabel til at knytte målere til grupper
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meter_group_members (
            group_id INT,
            meter_id INT,
            FOREIGN KEY (group_id) REFERENCES meter_groups (id),
            FOREIGN KEY (meter_id) REFERENCES meters (id),
            PRIMARY KEY (group_id, meter_id)
        )
        ''')

        conn.commit()
        cursor.close()
        conn.close()

    def add_meter(self, ip_address, meter_name, mac_address):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
            INSERT INTO meters (ip_address, meter_name, mac_address, created_at)
            VALUES (%s, %s, %s, %s)
            ''', (ip_address, meter_name, mac_address, current_time))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except mysql.connector.IntegrityError:
            return False
        except Exception as e:
            logging.error(f"Fejl ved tilføjelse af måler: {str(e)}")
            return False

    def get_meter_by_ip(self, ip_address):
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT * FROM meters WHERE ip_address = %s', (ip_address,))
        meter = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return meter

    def get_meter_by_mac(self, mac_address):
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT * FROM meters WHERE mac_address = %s', (mac_address,))
        meter = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return meter

    def get_meter_by_name(self, meter_name):
        """Hent måler information baseret på måler navn"""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT * FROM meters WHERE meter_name = %s', (meter_name,))
        meter = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return meter

    def get_all_meters(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT ip_address, meter_name, mac_address FROM meters')
        meters = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return meters

    def save_reading(self, ip_address, meter_name, total_energy, timestamp, mac_address=None):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO readings (ip_address, meter_name, total_energy, timestamp, mac_address)
        VALUES (%s, %s, %s, %s, %s)
        ''', (ip_address, meter_name, total_energy, timestamp, mac_address))
        
        conn.commit()
        cursor.close()
        conn.close()

    def batch_save_readings(self, readings):
        """Gem flere målinger på én gang for bedre performance"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.executemany('''
                INSERT INTO readings (ip_address, meter_name, total_energy, timestamp, mac_address)
                VALUES (%s, %s, %s, %s, %s)
            ''', readings)
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Fejl ved batch gemning af målinger: {str(e)}")
            return False

    def get_readings(self, meter_name, days=180):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        date_limit = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
        SELECT timestamp, total_energy 
        FROM readings 
        WHERE meter_name = %s AND timestamp > %s
        ORDER BY timestamp
        ''', (meter_name, date_limit))
        
        readings = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return readings

    def get_latest_reading(self, meter_name):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT timestamp, total_energy 
        FROM readings 
        WHERE meter_name = %s
        ORDER BY timestamp DESC
        LIMIT 1
        ''', (meter_name,))
        
        reading = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return reading

    def search_meters(self, search_term=''):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if search_term:
            cursor.execute('''
            SELECT DISTINCT meter_name 
            FROM meters 
            WHERE meter_name LIKE %s
            ''', (f'%{search_term}%',))
        else:
            cursor.execute('SELECT DISTINCT meter_name FROM meters')
            
        meters = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        return meters

    def create_meter_group(self, group_name):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
            INSERT INTO meter_groups (group_name, created_at)
            VALUES (%s, %s)
            ''', (group_name, current_time))
            
            group_id = cursor.lastrowid
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return group_id
        except mysql.connector.IntegrityError:
            return None
        except Exception as e:
            logging.error(f"Fejl ved oprettelse af målergruppe: {str(e)}")
            return None

    def add_meter_to_group(self, group_name, meter_name):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Find gruppe ID
            cursor.execute('SELECT id FROM meter_groups WHERE group_name = %s', (group_name,))
            group_result = cursor.fetchone()
            
            if not group_result:
                return False
                
            group_id = group_result[0]
            
            # Find måler ID
            cursor.execute('SELECT id FROM meters WHERE meter_name = %s', (meter_name,))
            meter_result = cursor.fetchone()
            
            if not meter_result:
                return False
                
            meter_id = meter_result[0]
            
            # Tilføj relation
            cursor.execute('''
            INSERT INTO meter_group_members (group_id, meter_id)
            VALUES (%s, %s)
            ''', (group_id, meter_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
        except Exception as e:
            logging.error(f"Fejl ved tilføjelse af måler til gruppe: {str(e)}")
            return False

    def get_meter_groups(self):
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('''
            SELECT g.group_name, GROUP_CONCAT(m.meter_name) as meters
            FROM meter_groups g
            LEFT JOIN meter_group_members gm ON g.id = gm.group_id
            LEFT JOIN meters m ON gm.meter_id = m.id
            GROUP BY g.group_name
            ''')
            
            groups = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Konverter meters string til liste
            for group in groups:
                if group['meters']:
                    group['meters'] = group['meters'].split(',')
                else:
                    group['meters'] = []
                    
            return groups
        except Exception as e:
            logging.error(f"Fejl ved hentning af målergrupper: {str(e)}")
            return []
