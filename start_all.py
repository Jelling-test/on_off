import subprocess
import sys
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def start_script(script_name):
    try:
        process = subprocess.Popen([sys.executable, script_name], 
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        logging.info(f"Startet {script_name}")
        return process
    except Exception as e:
        logging.error(f"Fejl ved start af {script_name}: {str(e)}")
        return None

def main():
    # Start alle scripts
    processes = {
        'Web Server': start_script('app.py'),
        'MQTT Client': start_script('mqtt_test.py'),
        'Backup Manager': start_script('backup_manager.py'),
        'Alert Manager': start_script('alert_manager.py')
    }
    
    # Hold scriptet kørende og genstart processerne hvis de crasher
    while True:
        for name, process in processes.items():
            if process and process.poll() is not None:  # Hvis processen er stoppet
                logging.warning(f"{name} er stoppet. Genstarter...")
                processes[name] = start_script(name.lower().replace(' ', '_') + '.py')
        
        time.sleep(10)

if __name__ == "__main__":
    main()
