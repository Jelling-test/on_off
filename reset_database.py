import sqlite3
from datetime import datetime

def reset_database():
    conn = sqlite3.connect('maaler_readings.db')
    cursor = conn.cursor()
    
    # Slet alle eksisterende målinger
    cursor.execute('DELETE FROM readings')
    
    # Opret tabellen igen hvis den ikke eksisterer
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT,
            meter_name TEXT,
            total_energy REAL,
            timestamp TEXT
        )
    ''')
    
    # Indsæt en ny startmåling med det korrekte tidspunkt
    current_time = "2025-02-18 13:53:07"  # Tidspunkt fra seneste MQTT besked
    raw_value = 358.551269  # Opdateret til den aktuelle værdi
    start_energy = raw_value / 1000.0  # Konverter til kWh
    
    # Indsæt måling for måler 902 med den korrekte værdi
    cursor.execute('''
        INSERT INTO readings (ip_address, meter_name, total_energy, timestamp)
        VALUES (?, ?, ?, ?)
    ''', ('obkBFBFD7F0', 'Måler 902', start_energy, current_time))
    
    # Formater energi med komma og 2 decimaler
    energy_formatted = format(round(start_energy, 2), '.2f').replace('.', ',')
    
    print(f"Nulstillet database og indsat startmåling:")
    print(f"Tidspunkt: {current_time}")
    print(f"Original værdi: {raw_value}")
    print(f"Konverteret energi: {energy_formatted} kWh")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    reset_database()
