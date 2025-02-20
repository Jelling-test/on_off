import sqlite3
from datetime import datetime

def fix_database():
    conn = sqlite3.connect('maaler_readings.db')
    cursor = conn.cursor()
    
    # Opdater alle målinger for måler 0884E7B7 til at bruge navnet "Måler 902"
    cursor.execute('''
        UPDATE readings 
        SET meter_name = 'Måler 902'
        WHERE ip_address LIKE '%0884E7B7%' OR meter_name LIKE '%0884E7B7%'
    ''')
    
    print(f"Opdateret {cursor.rowcount} rækker")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_database()
