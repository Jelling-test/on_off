import sqlite3

def fix_meter_names():
    conn = sqlite3.connect('maaler_readings.db')
    cursor = conn.cursor()
    
    # Opdater alle målinger for begge ID'er til at bruge navnet "Måler 902"
    cursor.execute('''
        UPDATE readings 
        SET meter_name = 'Måler 902'
        WHERE ip_address IN ('obk0884DD9F', 'obkBFBFD7F0') 
           OR meter_name IN ('Måler 0884DD9F', 'Måler BFBFD7F0')
    ''')
    
    print(f"Opdateret {cursor.rowcount} rækker")
    
    # Vis resultatet
    cursor.execute('''
        SELECT DISTINCT meter_name, ip_address
        FROM readings
        ORDER BY meter_name
    ''')
    
    print("\nUnikke måler navne og IP'er:")
    for row in cursor.fetchall():
        print(f"Navn: {row[0]}, IP: {row[1]}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_meter_names()
