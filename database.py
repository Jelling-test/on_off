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
        self._create_indexes()
        
    def _init_db(self):
        conn = mysql.connector.connect(**self.db_config)
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
        
        # Tilføj mac_address kolonne hvis den ikke findes
        try:
            cursor.execute('''
            ALTER TABLE readings 
            ADD COLUMN IF NOT EXISTS mac_address VARCHAR(255)
            ''')
        except Exception as e:
            logging.warning(f"Kunne ikke tilføje mac_address kolonne: {str(e)}")
        
        # Opret tabel til målergrupper
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meter_groups (
            id INT AUTO_INCREMENT PRIMARY KEY,
            group_name VARCHAR(255)
        )
        ''')
        
        # Opret tabel til måler-gruppe relationer
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meter_group_relations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            group_id INT,
            meter_name VARCHAR(255),
            FOREIGN KEY (group_id) REFERENCES meter_groups(id)
        )
        ''')
        
        cursor.close()
        conn.commit()
        conn.close()
    
    def _create_indexes(self):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        # Opret indeks på meter_name og timestamp
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_meter_name ON readings (meter_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON readings (timestamp)')
        
        cursor.close()
        conn.commit()
        conn.close()
    
    def add_meter(self, ip_address, meter_name, mac_address):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT * FROM readings WHERE meter_name = %s LIMIT 1', (meter_name,))
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(
                'INSERT INTO readings (ip_address, meter_name, total_energy, timestamp, mac_address) VALUES (%s, %s, %s, %s, %s)',
                (ip_address, meter_name, 0, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), mac_address)
            )
            
        cursor.close()
        conn.commit()
        conn.close()
        
    def get_meter_by_ip(self, ip_address):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT DISTINCT meter_name FROM readings WHERE ip_address = %s', (ip_address,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result['meter_name'] if result else None
        
    def get_meter_by_mac(self, mac_address):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT DISTINCT meter_name FROM readings WHERE mac_address = %s', (mac_address,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return result['meter_name'] if result else None
    
    def get_all_meters(self):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT DISTINCT meter_name, ip_address, COALESCE(mac_address, "") as mac_address FROM readings')
        meters = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Konverter til liste af tupler for kompatibilitet med eksisterende kode
        return [(m['ip_address'], m['meter_name'], m['mac_address']) for m in meters]
    
    def save_reading(self, ip_address, meter_name, total_energy, timestamp):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO readings (ip_address, meter_name, total_energy, timestamp) VALUES (%s, %s, %s, %s)',
            (ip_address, meter_name, total_energy, timestamp)
        )
        
        cursor.close()
        conn.commit()
        conn.close()
    
    def batch_save_readings(self, readings):
        if not readings:
            return
            
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        insert_query = '''
        INSERT INTO readings (ip_address, meter_name, total_energy, timestamp)
        VALUES (%s, %s, %s, %s)
        '''
        
        cursor.executemany(insert_query, readings)
        
        cursor.close()
        conn.commit()
        conn.close()
    
    def get_readings(self, meter_name, days=180):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor(dictionary=True)
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
        SELECT timestamp, total_energy 
        FROM readings 
        WHERE meter_name = %s AND timestamp >= %s
        ORDER BY timestamp
        ''', (meter_name, start_date))
        
        readings = cursor.fetchall()
        
        # Konverter til liste af dictionaries med konsistent format
        return [{'timestamp': r['timestamp'].strftime('%Y-%m-%d %H:%M:%S'), 'total_energy': r['total_energy']} for r in readings]
    
    def search_meters(self, search_term=''):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor(dictionary=True)
        
        search_pattern = f'%{search_term}%'
        cursor.execute('SELECT DISTINCT meter_name FROM readings WHERE meter_name LIKE %s', (search_pattern,))
        meters = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return [meter['meter_name'] for meter in meters]
    
    def cleanup_old_data(self):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('DELETE FROM readings WHERE timestamp < %s', (cutoff_date,))
        
        cursor.close()
        conn.commit()
        conn.close()
    
    def create_meter_group(self, group_name):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        cursor.execute('INSERT INTO meter_groups (group_name) VALUES (%s)', (group_name,))
        group_id = cursor.lastrowid
        
        cursor.close()
        conn.commit()
        conn.close()
        
        return group_id
    
    def add_meter_to_group(self, group_name, meter_name):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor()
        
        # Find group_id
        cursor.execute('SELECT id FROM meter_groups WHERE group_name = %s', (group_name,))
        result = cursor.fetchone()
        if result:
            group_id = result[0]
            cursor.execute(
                'INSERT INTO meter_group_relations (group_id, meter_name) VALUES (%s, %s)',
                (group_id, meter_name)
            )
        
        cursor.close()
        conn.commit()
        conn.close()
    
    def get_meter_groups(self):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
        SELECT g.group_name, GROUP_CONCAT(r.meter_name) as meters
        FROM meter_groups g
        LEFT JOIN meter_group_relations r ON g.id = r.group_id
        GROUP BY g.group_name
        ''')
        
        groups = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return groups
    
    def get_latest_reading(self, meter_name):
        conn = mysql.connector.connect(**self.db_config)
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('''
        SELECT total_energy, timestamp 
        FROM readings 
        WHERE meter_name = %s 
        ORDER BY timestamp DESC 
        LIMIT 1
        ''', (meter_name,))
        
        reading = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return reading
