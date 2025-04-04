from fastapi import FastAPI, WebSocket, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio
import uvicorn
from datetime import datetime
import sqlite3
import csv
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conn = sqlite3.connect("drilling_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS drilling_events (
    timestamp TEXT, bit_depth REAL, wobs REAL, rpm REAL, torque REAL, flow_rate REAL,
    mud_density REAL, annular_pressure REAL, predicted_rop REAL,
    mech_stick_alert INTEGER, diff_stick_alert INTEGER, hole_clean_alert INTEGER, mud_loss_alert INTEGER
)''')
conn.commit()

class DrillingData(BaseModel):
    bit_depth: float
    wobs: float
    rpm: float
    torque: float
    flow_rate: float
    mud_density: float
    annular_pressure: float

subscribers = []

@app.post("/ingest")
async def ingest_data(data: DrillingData):
    from edge.processor import process_data
    alerts = process_data(data)
    payload = data.dict()
    payload.update(alerts)
    payload['timestamp'] = datetime.utcnow().isoformat()

    cursor.execute('''INSERT INTO drilling_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        payload['timestamp'], payload['bit_depth'], payload['wobs'], payload['rpm'], payload['torque'],
        payload['flow_rate'], payload['mud_density'], payload['annular_pressure'],
        payload['predicted_rop'], int(payload['mechanical_sticking_alert']), int(payload['differential_sticking_alert']),
        int(payload['hole_cleaning_alert']), int(payload['mud_loss_alert'])
    ))
    conn.commit()

    alerts_active = [k for k, v in alerts.items() if isinstance(v, bool) and v]
    payload['priority'] = 'HIGH' if len(alerts_active) > 2 else ('MEDIUM' if len(alerts_active) > 0 else 'LOW')

    for websocket in subscribers:
        await websocket.send_json(payload)
    return {"status": "broadcasted", "alerts": alerts_active}

@app.get("/history")
def get_history():
    cursor.execute("SELECT * FROM drilling_events ORDER BY timestamp DESC LIMIT 50")
    rows = cursor.fetchall()
    return [
        {
            "timestamp": r[0], "bit_depth": r[1], "wobs": r[2], "rpm": r[3], "torque": r[4],
            "flow_rate": r[5], "mud_density": r[6], "annular_pressure": r[7],
            "predicted_rop": r[8], "mechanical_sticking_alert": bool(r[9]),
            "differential_sticking_alert": bool(r[10]), "hole_cleaning_alert": bool(r[11]),
            "mud_loss_alert": bool(r[12])
        } for r in rows
    ]

@app.get("/export")
def export_csv():
    cursor.execute("SELECT * FROM drilling_events ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    headers = ["timestamp", "bit_depth", "wobs", "rpm", "torque", "flow_rate",
               "mud_density", "annular_pressure", "predicted_rop",
               "mechanical_sticking_alert", "differential_sticking_alert",
               "hole_cleaning_alert", "mud_loss_alert"]

    stream = io.StringIO()
    csv_writer = csv.writer(stream)
    csv_writer.writerow(headers)
    csv_writer.writerows(rows)
    stream.seek(0)
    return StreamingResponse(iter([stream.read()]), media_type="text/csv",
                              headers={"Content-Disposition": "attachment; filename=drilling_data.csv"})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    subscribers.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        print("WebSocket closed", e)
    finally:
        subscribers.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)