import sqlite3
from datetime import datetime

def check_readings():
    conn = sqlite3.connect('maaler_readings.db')
    cursor = conn.cursor()
    
    print("\nSeneste 10 målinger for Måler 902:")
    cursor.execute('''
        SELECT timestamp, total_energy, meter_name, ip_address
        FROM readings 
        WHERE meter_name = 'Måler 902'
        ORDER BY timestamp DESC
        LIMIT 10
    ''')
    
    readings = cursor.fetchall()
    for reading in readings:
        print(f"Tid: {reading[0]}, Energi: {reading[1]:.3f} kWh, Navn: {reading[2]}, IP: {reading[3]}")
    
    print("\nAntal målinger per måler:")
    cursor.execute('''
        SELECT meter_name, COUNT(*) as antal, 
               MIN(timestamp) as første_måling,
               MAX(timestamp) as sidste_måling
        FROM readings 
        GROUP BY meter_name
    ''')
    
    stats = cursor.fetchall()
    for stat in stats:
        print(f"\nMåler: {stat[0]}")
        print(f"Antal målinger: {stat[1]}")
        print(f"Første måling: {stat[2]}")
        print(f"Sidste måling: {stat[3]}")
    
    conn.close()

if __name__ == "__main__":
    check_readings()
