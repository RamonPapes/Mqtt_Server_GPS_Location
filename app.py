from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO
from threading import Thread
import sqlite3
import paho.mqtt.client as mqtt
import json
import time

DATABASE = "./db.sqlite"

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            timestamp TEXT NOT NULL,
            error REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_location(lat, lon, timestamp, error):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO locations (latitude, longitude, timestamp, error)
        VALUES (?, ?, ?, ?)
    """, (lat, lon, timestamp, error))
    conn.commit()
    conn.close()

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        lat = payload.get("latitude")
        lon = payload.get("longitude")
        timestamp = payload.get("timestamp")
        error = payload.get("error")

        if lat is None or lon is None or timestamp is None or error is None:
            return

        save_location(lat, lon, timestamp, error)
        print(f"✅ Localização salva: {payload}")

        # ✅ Envia atualização instantânea para todos os frontends conectados
        socketio.emit("nova_localizacao", payload)

    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Conectado ao broker MQTT.")
        client.subscribe("esp32/gps")
    else:
        print("Erro ao conectar ao broker:", rc)

@app.route("/locations", methods=["GET"])
def get_locations():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM locations ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()

    data = [
        {"id": r[0], "latitude": r[1], "longitude": r[2], "timestamp": r[3], "error": r[4]}
        for r in rows
    ]

    return jsonify({"status": 1, "data": data})

@app.route("/")
def home():
    return send_from_directory("templates", "index.html")

if __name__ == "__main__":
    init_db()

    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect("test.mosquitto.org", 1883, 60)
    Thread(target=mqtt_client.loop_forever).start()

    socketio.run(app, host="0.0.0.0", port=5000)
