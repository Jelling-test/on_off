import shutil
import os
from datetime import datetime
import schedule
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

class BackupManager:
    def __init__(self, source_db, backup_dir):
        self.source_db = source_db
        self.backup_dir = backup_dir
        
    def create_backup(self):
        try:
            # Opret backup mappe hvis den ikke findes
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
            
            # Generer filnavn med dato
            current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            backup_filename = f'maaler_readings_backup_{current_time}.db'
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Kopier databasen
            shutil.copy2(self.source_db, backup_path)
            
            # Behold kun de seneste 7 backups
            self._cleanup_old_backups()
            
            logging.info(f"Backup oprettet: {backup_path}")
            return True
            
        except Exception as e:
            logging.error(f"Fejl ved backup: {str(e)}")
            return False
    
    def _cleanup_old_backups(self):
        try:
            # Find alle backup filer
            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('maaler_readings_backup_') and filename.endswith('.db'):
                    filepath = os.path.join(self.backup_dir, filename)
                    backups.append((filepath, os.path.getmtime(filepath)))
            
            # Sorter efter dato (nyeste først)
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # Slet gamle backups (behold kun de 7 nyeste)
            for filepath, _ in backups[7:]:
                os.remove(filepath)
                logging.info(f"Slettet gammel backup: {filepath}")
                
        except Exception as e:
            logging.error(f"Fejl ved oprydning af gamle backups: {str(e)}")

def start_backup_schedule(backup_dir):
    backup_manager = BackupManager('maaler_readings.db', backup_dir)
    
    # Lav backup hver dag kl 02:00
    schedule.every().day.at("02:00").do(backup_manager.create_backup)
    
    # Lav også en backup med det samme når scriptet starter
    backup_manager.create_backup()
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # Erstat med den ønskede netværkssti
    BACKUP_DIR = r"\\SERVER\Backup\MaalerData"
    start_backup_schedule(BACKUP_DIR)
