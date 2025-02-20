import sqlite3
from datetime import datetime

def fix_timestamps():
    conn = sqlite3.connect('maaler_readings.db')
    cursor = conn.cursor()
    
    # Sæt alle timestamps til nuværende tid
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        UPDATE readings 
        SET timestamp = ?
        WHERE meter_name = 'Måler 902'
    ''', (current_time,))
    
    print(f"Opdateret {cursor.rowcount} rækker til tidspunkt: {current_time}")
    
    # Vis de seneste målinger
    cursor.execute('''
        SELECT timestamp, total_energy, ip_address
        FROM readings
        WHERE meter_name = 'Måler 902'
        ORDER BY timestamp DESC
        LIMIT 5
    ''')
    
    print("\nSeneste målinger for Måler 902:")
    for row in cursor.fetchall():
        print(f"Tid: {row[0]}, Energi: {row[1]:.3f} kWh, IP: {row[2]}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_timestamps()
