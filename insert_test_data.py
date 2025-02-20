import sqlite3
from datetime import datetime, timedelta

def insert_test_data():
    conn = sqlite3.connect('maaler_readings.db')
    cursor = conn.cursor()
    
    # Indsæt test data for måler 902
    meter_id = "obk0884DD9F"
    meter_name = "Måler 902"
    current_time = datetime.now()
    
    # Simuler målinger over de sidste 6 timer
    for i in range(6):
        timestamp = (current_time - timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S')
        energy = 14.260  # Den aktuelle værdi du nævnte
        
        cursor.execute('''
            INSERT INTO readings (ip_address, meter_name, total_energy, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (meter_id, meter_name, energy, timestamp))
    
    conn.commit()
    conn.close()
    print("Test data indsat i databasen")

if __name__ == "__main__":
    insert_test_data()
