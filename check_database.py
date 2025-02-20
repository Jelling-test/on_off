import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

def check_database():
    try:
        # Forbind til databasen
        conn = sqlite3.connect('maaler_readings.db')
        cursor = conn.cursor()
        
        # Vis tabel struktur
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='readings'")
        table_info = cursor.fetchone()
        logging.info(f"\nTabel struktur:\n{table_info[0] if table_info else 'Ingen tabel fundet!'}")
        
        # Tæl antal rækker
        cursor.execute("SELECT COUNT(*) FROM readings")
        count = cursor.fetchone()[0]
        logging.info(f"\nAntal målinger i databasen: {count}")
        
        # Vis unikke målere
        cursor.execute("SELECT DISTINCT meter_name FROM readings")
        meters = cursor.fetchall()
        logging.info("\nUnikke målere i databasen:")
        for meter in meters:
            logging.info(f"- {meter[0]}")
            
        # Vis de seneste 5 målinger
        cursor.execute("""
            SELECT meter_name, total_energy, timestamp 
            FROM readings 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        readings = cursor.fetchall()
        logging.info("\nSeneste 5 målinger:")
        for reading in readings:
            logging.info(f"Måler: {reading[0]}, Energi: {reading[1]} kWh, Tid: {reading[2]}")
            
    except sqlite3.Error as e:
        logging.error(f"Database fejl: {str(e)}")
    except Exception as e:
        logging.error(f"Generel fejl: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_database()
