# Energimåler System

Et system til at overvåge og administrere energimålere via MQTT protokollen. Systemet er designet til at håndtere mange målere samtidigt og vise deres data i realtid.

## Funktioner

### Måler Administration
- ✅ Tilføj nye målere via IP eller MAC adresse
- ✅ Slet målere (beskyttet med sikkerhedskode)
- ✅ Vis liste over alle installerede målere
- ✅ Realtidsvisning af målerdata
- ✅ Grafisk visning af historisk forbrug

### Målergrupper
- ✅ Opret og administrer grupper af målere
- ✅ Tilføj/fjern målere fra grupper
- ✅ Se samlet forbrug for grupper
- ✅ Automatisk opdatering af gruppedata

### Data Håndtering
- ✅ Automatisk indsamling af målerdata via MQTT
- ✅ Batch processing af målinger for bedre performance
- ✅ SQLite database med optimerede indekser
- ✅ Fejlhåndtering og automatisk genoprettelse af forbindelser

## Installation

1. Installer Python 3.8 eller nyere
2. Installer afhængigheder:
   ```bash
   pip install -r requirements.txt
   ```
3. Konfigurer MQTT indstillinger i mqtt_test.py
4. Start systemet:
   ```bash
   python app.py        # Start webserver
   python mqtt_test.py  # Start MQTT klient
   ```

## Konfiguration

### MQTT Indstillinger
- Broker: 192.168.0.208
- Port: 1883
- Bruger: homeassistant
- Password: password123

### Database
SQLite database (maaler_readings.db) med følgende tabeller:
- meters: Information om målere
- readings: Måleraflæsninger
- meter_groups: Målergrupper
- meter_group_members: Gruppe medlemskab

## Sikkerhed
- Sletning af målere kræver sikkerhedskode (2012)
- Validering af input data
- Beskyttelse mod SQL injection

## Kendte Begrænsninger
1. Målere skal være på samme netværk som serveren
2. Tidszonen er hardkodet til lokal tid
3. SQLite kan have begrænsninger ved meget høj samtidig brug

## Planlagte Forbedringer
1. [ ] Implementer brugeradministration med forskellige adgangsniveauer
2. [ ] Tilføj eksport af data til CSV/Excel
3. [ ] Implementer backup system for databasen
4. [ ] Tilføj e-mail notifikationer ved fejl
5. [ ] Tilføj support for flere målertyper
6. [ ] Implementer caching for bedre performance
7. [ ] Tilføj API dokumentation
8. [ ] Tilføj flere grafer og visualiseringer
9. [ ] Implementer automatisk opdatering af firmware
10. [ ] Tilføj support for SSL/TLS i MQTT forbindelsen

## Bidrag
Projektet er udviklet af Jelling Camping. For spørgsmål eller bidrag, kontakt os venligst.

## Licens
Dette projekt er lukket source og må kun bruges med tilladelse fra Jelling Camping.
