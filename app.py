from flask import Flask, render_template, jsonify, request
from database import MaalerDatabase
import paho.mqtt.client as mqtt
import json
import requests
import logging
import re

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
db = MaalerDatabase()

def discover_mac_address(ip_address):
    """Find MAC adressen for en måler ved at spørge dens info endpoint"""
    try:
        logging.info(f"Forsøger at hente MAC adresse fra {ip_address}")
        response = requests.get(f"http://{ip_address}/info", timeout=5)
        logging.info(f"Response status: {response.status_code}")
        logging.info(f"Response body: {response.text}")
        
        if response.status_code == 200:
            mac_match = re.search(r'Device MAC: ([0-9A-Fa-f:]+)', response.text)
            if mac_match:
                mac_address = mac_match.group(1)
                mac_address = mac_address.replace(':', '')  # Fjern : fra MAC adressen
                logging.info(f"Fandt MAC adresse: {mac_address}")
                return mac_address
            else:
                logging.error("Ingen MAC adresse fundet i response")
    except Exception as e:
        logging.error(f"Fejl ved hentning af MAC adresse: {str(e)}")
    return None

@app.route('/')
def index():
    meters = db.get_all_meters()
    return render_template('index.html', meters=meters)

@app.route('/get_all_meters')
def get_all_meters():
    meters = db.get_all_meters()
    meter_list = []
    for ip, name, mac in meters:
        meter_list.append({
            'ip': ip,
            'name': name,
            'mac': mac
        })
    return jsonify(meter_list)

@app.route('/add_meter', methods=['POST'])
def add_meter():
    try:
        ip_address = request.form['ip_address']
        meter_name = request.form['meter_name']
        
        logging.info(f"Forsøger at tilføje måler: {meter_name} på IP: {ip_address}")
        
        # Find MAC adressen
        mac_address = discover_mac_address(ip_address)
        if not mac_address:
            error_msg = 'Kunne ikke finde MAC adressen for måleren. Tjek at IP adressen er korrekt og at måleren er online.'
            logging.error(error_msg)
            return jsonify({'success': False, 'error': error_msg})
        
        # Tilføj måleren til databasen
        if db.add_meter(ip_address, meter_name, mac_address):
            logging.info(f"Måler tilføjet: {meter_name} (MAC: {mac_address})")
            return jsonify({'success': True, 'mac_address': mac_address})
        else:
            error_msg = 'Måler med denne IP eller navn findes allerede'
            logging.error(error_msg)
            return jsonify({'success': False, 'error': error_msg})
            
    except Exception as e:
        error_msg = f"Uventet fejl: {str(e)}"
        logging.error(error_msg)
        return jsonify({'success': False, 'error': error_msg})

@app.route('/add_meter_mac', methods=['POST'])
def add_meter_mac():
    try:
        mac_address = request.form['mac_address']
        meter_name = request.form['meter_name']
        
        logging.info(f"Forsøger at tilføje måler: {meter_name} med MAC: {mac_address}")
        
        # Tilføj måleren til databasen uden IP adresse
        if db.add_meter(None, meter_name, mac_address):
            logging.info(f"Måler tilføjet via MAC: {meter_name} (MAC: {mac_address})")
            return jsonify({'success': True})
        else:
            error_msg = 'Måler med denne MAC adresse eller navn findes allerede'
            logging.error(error_msg)
            return jsonify({'success': False, 'error': error_msg})
            
    except Exception as e:
        error_msg = f"Uventet fejl: {str(e)}"
        logging.error(error_msg)
        return jsonify({'success': False, 'error': error_msg})

@app.route('/search')
def search_meters():
    term = request.args.get('term', '')
    meters = db.search_meters(term)
    return jsonify(meters)

@app.route('/get_readings')
def get_readings():
    meter_name = request.args.get('meter_name')
    if not meter_name:
        return jsonify({'error': 'Ingen måler valgt'}), 400
        
    readings = db.get_readings(meter_name)
    latest_reading = db.get_latest_reading(meter_name)
    
    if not readings:
        # Hvis der ikke er nogen målinger, returner tomme arrays men inkluder måler navn
        return jsonify({
            'dates': [],
            'values': [],
            'latest': None,
            'meter_name': meter_name
        })
    
    dates = [r[0] for r in readings]
    # Konverter Wh til kWh ved at dividere med 1000
    values = [round(float(r[1]) / 1000, 2) for r in readings]
    
    # Formater latest data korrekt med value og timestamp felter
    latest = None
    if latest_reading and len(latest_reading) >= 2:
        latest = {
            'timestamp': latest_reading[0].strftime('%Y-%m-%d %H:%M:%S') if latest_reading[0] else None,
            # Konverter Wh til kWh og formater med 2 decimaler
            'value': round(float(latest_reading[1]) / 1000, 2) if latest_reading[1] is not None else None
        }
    
    return jsonify({
        'dates': dates,
        'values': values,
        'latest': latest,
        'meter_name': meter_name
    })

@app.route('/create_meter_group', methods=['POST'])
def create_meter_group():
    try:
        group_name = request.form['group_name']
        group_id = db.create_meter_group(group_name)
        if group_id:
            return jsonify({'success': True, 'group_id': group_id})
        return jsonify({'success': False, 'error': 'Gruppe findes allerede'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/add_meter_to_group', methods=['POST'])
def add_meter_to_group():
    try:
        group_name = request.form['group_name']
        meter_name = request.form['meter_name']
        if db.add_meter_to_group(group_name, meter_name):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Kunne ikke tilføje måler til gruppe'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_meter_groups')
def get_meter_groups():
    try:
        groups = db.get_meter_groups()
        return jsonify(groups)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/graph_data/<meter_name>')
def graph_data(meter_name):
    # Tjek om måleren eksisterer
    meters = db.search_meters(meter_name)
    if meter_name not in meters:
        return jsonify({'error': f'Måler "{meter_name}" findes ikke'}), 404

    days = int(request.args.get('days', 180))
    readings = db.get_readings(meter_name, days)
    
    if not readings:
        return jsonify({'error': f'Ingen data fundet for måler "{meter_name}"'}), 404
    
    # Forbered data til plotly
    dates = [r[0] for r in readings]
    energy = [r[1] for r in readings]
    
    # Find seneste tidspunkt og energi
    latest_reading_time = max(dates) if dates else "Ingen data"
    latest_energy = energy[-1] if energy else 0
    
    if latest_reading_time != "Ingen data":
        latest_reading_time = latest_reading_time.strftime('%d-%m-%Y %H:%M:%S')
    
    # Formater energi med komma og 2 decimaler
    energy_formatted = format(round(latest_energy, 2), '.2f').replace('.', ',')
    
    # Opret linjegraf
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=energy,
        mode='lines',  # Brug lines i stedet for bars
        line=dict(
            color='rgb(49,130,189)',
            width=2
        ),
        name='Total Energi'
    ))
    
    # Konfigurer layout for A4 landskab print
    fig.update_layout(
        title={
            'text': f'Energiforbrug - {meter_name}<br>Seneste aflæsning: {latest_reading_time}<br>Forbrug: {energy_formatted} kWh',
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title='Dato',
        yaxis_title='Total Energi (kWh)',
        width=1123,  # A4 landskab i pixels (297mm)
        height=794,  # A4 landskab i pixels (210mm)
        margin=dict(l=50, r=50, t=100, b=50),
        paper_bgcolor='white',
        plot_bgcolor='white',
        showlegend=False,  # Skjul legend da vi kun har én linje
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=1
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            gridwidth=1,
            rangemode='nonnegative',  # Forhindrer negative værdier
            range=[0, None]  # Start ved 0, automatisk maksimum
        )
    )
    
    return json.dumps(fig.to_dict())

@app.route('/overview')
def overview():
    try:
        # Hent alle målere
        meters = db.get_all_meters()
        meter_data = []
        
        for ip, name, mac in meters:
            # Hent seneste måling for hver måler
            latest = db.get_latest_reading(name)
            if latest:
                timestamp, value = latest
                meter_data.append({
                    'name': name,
                    'latest_reading': value,
                    'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else None
                })
        
        # Sorter efter seneste måling (højeste værdi først)
        meter_data.sort(key=lambda x: x['latest_reading'] if x['latest_reading'] is not None else 0, reverse=True)
        
        return jsonify({
            'success': True,
            'meters': meter_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/get_total_consumption')
def get_total_consumption():
    try:
        # Hent alle målere
        meters = db.get_all_meters()
        total = 0
        
        for ip, name, mac in meters:
            # Hent seneste måling for hver måler
            latest = db.get_latest_reading(name)
            if latest and latest[1] is not None:
                total += latest[1]
        
        return jsonify({
            'success': True,
            'total': total
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/delete_meter', methods=['POST'])
def delete_meter():
    try:
        meter_name = request.form['meter_name']
        if db.delete_meter(meter_name):
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Kunne ikke slette måler'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/toggle_power', methods=['POST'])
def toggle_power():
    """Tænder eller slukker for en måler.
    Understøtter to forskellige MQTT kommandoformater:
    1. cmnd/obkMAC/Power med tom streng for toggle
    2. obkMAC/0/set med '0' for sluk, '1' for tænd
    """
    try:
        data = request.get_json()
        meter_name = data.get('meter_name')
        desired_state = data.get('state')  # None/tom for toggle, '0' for sluk, '1' for tænd
        
        if not meter_name:
            return jsonify({'error': 'Manglende måler navn'}), 400
            
        # Find målerens information i databasen
        meter = db.get_meter_by_name(meter_name)
        if not meter or not meter['mac_address']:
            return jsonify({'error': 'Måler ikke fundet eller mangler MAC adresse'}), 404
            
        mac_address = meter['mac_address']
        # Tag kun de sidste 8 tegn af MAC adressen
        short_mac = mac_address[-8:]
        
        # MQTT setup
        mqtt_client = mqtt.Client()
        mqtt_client.username_pw_set("homeassistant", "password123")
        
        try:
            mqtt_client.connect("192.168.9.61", 1890, 60)
        except Exception as e:
            return jsonify({'error': f'Kunne ikke forbinde til MQTT broker: {str(e)}'}), 500
        
        # Definer kommandoer for begge typer målere
        commands = [
            # Type 1: Ny kommandostruktur (som måler 903)
            {
                'topic': f"obk{short_mac}/0/set",
                'payload': desired_state if desired_state in ['0', '1'] else '1',  # Default til tænd hvis ingen state
                'delay': 2  # Sekunder at vente efter kommando
            },
            # Type 2: Gammel kommandostruktur (som måler 902)
            {
                'topic': f"cmnd/obk{short_mac}/Power",
                'payload': "",  # Tom streng for at toggle
                'delay': 0  # Ingen ventetid nødvendig
            }
        ]
        
        success = False
        used_command = None
        
        # Prøv begge kommandotyper
        for cmd in commands:
            try:
                logging.info(f"Sender kommando til {cmd['topic']} med payload: '{cmd['payload']}'")
                result = mqtt_client.publish(cmd['topic'], cmd['payload'], qos=1)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    if cmd['delay'] > 0:
                        import time
                        time.sleep(cmd['delay'])
                    
                    success = True
                    used_command = cmd
                    logging.info(f"Kommando sendt succesfuldt til {cmd['topic']}")
                    break
                    
            except Exception as e:
                logging.error(f"Fejl ved sending til {cmd['topic']}: {str(e)}")
                continue
        
        mqtt_client.disconnect()
        
        if not success:
            return jsonify({'error': 'Kunne ikke sende kommando til nogen af de forsøgte kommandoformater'}), 500
            
        return jsonify({
            'success': True, 
            'meter': meter_name,
            'mac': short_mac,
            'topic_used': used_command['topic'],
            'payload_used': used_command['payload']
        })
        
    except Exception as e:
        logging.error(f"Fejl i toggle_power: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
