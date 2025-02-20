import sqlite3
from datetime import datetime, timedelta
import logging

class MaalerDatabase:
    def __init__(self, db_file='maaler_readings.db'):
        self.db_file = db_file
        self._init_db()
        self._create_indexes()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Opret tabel til målinger hvis den ikke findes
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            meter_name TEXT,
            total_energy REAL,
            timestamp TEXT
        )
        ''')

        # Opret tabel til måler-konfiguration med kun MAC adresse som unik
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            meter_name TEXT,
            mac_address TEXT UNIQUE,
            created_at TEXT
        )
        ''')

        # Opret tabel til målergrupper
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meter_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_name TEXT UNIQUE,
            created_at TEXT
        )
        ''')

        # Opret tabel til at knytte målere til grupper
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meter_group_members (
            group_id INTEGER,
            meter_id INTEGER,
            FOREIGN KEY (group_id) REFERENCES meter_groups (id),
            FOREIGN KEY (meter_id) REFERENCES meters (id),
            PRIMARY KEY (group_id, meter_id)
        )
        ''')

        conn.commit()
        conn.close()

    def _create_indexes(self):
        """Opret indekser for bedre performance"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Indeks på meter_name i readings tabellen
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_readings_meter_name 
                ON readings(meter_name)
            ''')
            
            # Indeks på timestamp i readings tabellen
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_readings_timestamp 
                ON readings(timestamp)
            ''')
            
            # Indeks på meter_name og timestamp kombineret
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_readings_meter_timestamp 
                ON readings(meter_name, timestamp)
            ''')
            
            conn.commit()
        except Exception as e:
            logging.error(f"Fejl ved oprettelse af indekser: {str(e)}")
        finally:
            conn.close()
            
    def add_meter(self, ip_address, meter_name, mac_address):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
            INSERT INTO meters (ip_address, meter_name, mac_address, created_at)
            VALUES (?, ?, ?, ?)
            ''', (ip_address, meter_name, mac_address, current_time))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"Fejl ved tilføjelse af måler: {str(e)}")
            return False

    def get_meter_by_ip(self, ip_address):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM meters WHERE ip_address = ?', (ip_address,))
        meter = cursor.fetchone()
        
        conn.close()
        return meter

    def get_meter_by_mac(self, mac_address):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM meters WHERE mac_address = ?', (mac_address,))
        meter = cursor.fetchone()
        
        conn.close()
        return meter

    def get_all_meters(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT ip_address, meter_name, mac_address FROM meters')
        meters = cursor.fetchall()
        
        conn.close()
        return meters

    def save_reading(self, ip_address, meter_name, total_energy, timestamp):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO readings (ip_address, meter_name, total_energy, timestamp)
        VALUES (?, ?, ?, ?)
        ''', (ip_address, meter_name, total_energy, timestamp))
        
        conn.commit()
        conn.close()

    def batch_save_readings(self, readings):
        """Gem flere målinger på én gang for bedre performance"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.executemany('''
                INSERT INTO readings (ip_address, meter_name, total_energy, timestamp)
                VALUES (?, ?, ?, ?)
            ''', readings)
            
            conn.commit()
            return True
        except Exception as e:
            logging.error(f"Fejl ved batch gemning af målinger: {str(e)}")
            return False
        finally:
            conn.close()

    def get_readings(self, meter_name, days=180):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        date_limit = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
        SELECT timestamp, total_energy 
        FROM readings 
        WHERE meter_name = ? AND timestamp > ?
        ORDER BY timestamp
        ''', (meter_name, date_limit))
        
        readings = cursor.fetchall()
        conn.close()
        
        return readings

    def search_meters(self, search_term=''):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        if search_term:
            cursor.execute('''
            SELECT DISTINCT meter_name 
            FROM readings 
            WHERE meter_name LIKE ?
            ''', (f'%{search_term}%',))
        else:
            cursor.execute('SELECT DISTINCT meter_name FROM readings')
            
        meters = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return meters

    def cleanup_old_data(self):
        """Slet data ældre end 6 måneder"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('DELETE FROM readings WHERE timestamp < ?', (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count

    def create_meter_group(self, group_name):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
            INSERT INTO meter_groups (group_name, created_at)
            VALUES (?, ?)
            ''', (group_name, current_time))
            
            group_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return group_id
        except sqlite3.IntegrityError:
            return None
        except Exception as e:
            logging.error(f"Fejl ved oprettelse af målergruppe: {str(e)}")
            return None

    def add_meter_to_group(self, group_name, meter_name):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Find gruppe ID
            cursor.execute('SELECT id FROM meter_groups WHERE group_name = ?', (group_name,))
            group_result = cursor.fetchone()
            if not group_result:
                conn.close()
                return False
            
            group_id = group_result[0]
            
            # Find måler ID
            cursor.execute('SELECT id FROM meters WHERE meter_name = ?', (meter_name,))
            meter_result = cursor.fetchone()
            if not meter_result:
                conn.close()
                return False
                
            meter_id = meter_result[0]
            
            # Tilføj måler til gruppe
            cursor.execute('''
            INSERT OR IGNORE INTO meter_group_members (group_id, meter_id)
            VALUES (?, ?)
            ''', (group_id, meter_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Fejl ved tilføjelse af måler til gruppe: {str(e)}")
            return False

    def get_meter_groups(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT g.group_name, GROUP_CONCAT(m.meter_name)
        FROM meter_groups g
        LEFT JOIN meter_group_members gm ON g.id = gm.group_id
        LEFT JOIN meters m ON gm.meter_id = m.id
        GROUP BY g.id, g.group_name
        ''')
        
        groups = cursor.fetchall()
        conn.close()
        
        # Konverter til liste af dictionaries
        result = []
        for group_name, meter_names in groups:
            meters = meter_names.split(',') if meter_names else []
            result.append({
                'name': group_name,
                'meters': meters
            })
        return result

    def get_latest_reading(self, meter_name):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT timestamp, total_energy
        FROM readings
        WHERE meter_name = ?
        ORDER BY timestamp DESC
        LIMIT 1
        ''', (meter_name,))
        
        reading = cursor.fetchone()
        conn.close()
        
        if reading:
            return {
                'timestamp': reading[0],
                'value': reading[1]
            }
        return None

    def delete_meter(self, meter_name):
        """Slet en måler og alle dens målinger"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Start en transaktion
            cursor.execute('BEGIN TRANSACTION')
            
            try:
                # Fjern måleren fra alle grupper først
                cursor.execute('''
                    DELETE FROM meter_group_members 
                    WHERE meter_id IN (
                        SELECT id FROM meters WHERE meter_name = ?
                    )
                ''', (meter_name,))
                
                # Slet alle målinger for måleren
                cursor.execute('DELETE FROM readings WHERE meter_name = ?', (meter_name,))
                
                # Slet selve måleren
                cursor.execute('DELETE FROM meters WHERE meter_name = ?', (meter_name,))
                
                # Hvis vi når hertil uden fejl, commit transaktionen
                conn.commit()
                return True
                
            except Exception as e:
                # Hvis der sker en fejl, rul tilbage
                cursor.execute('ROLLBACK')
                raise e
                
        except Exception as e:
            logging.error(f"Fejl ved sletning af måler: {str(e)}")
            return False
        finally:
            conn.close()
