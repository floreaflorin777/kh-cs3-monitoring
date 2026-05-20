from flask import Flask, request, jsonify
import pymssql
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")

app = Flask(__name__)

# Check if the request contains API key

def check_api_key():
    incoming_key = request.headers.get("X-API-Key")
    if not API_KEY:
        return True
    return incoming_key == API_KEY

# Establish database connection

def get_db_connection():
    conn = pymssql.connect(
        host=os.getenv('DB_SERVER'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
    )
    return conn

# Initialize database

def initialize_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'measurements')
            CREATE TABLE measurements (
                id INT IDENTITY(1,1) PRIMARY KEY,
                timestamp DATETIME DEFAULT GETDATE(),
                hostname NVARCHAR(100) NOT NULL,
                metric NVARCHAR(50),
                value FLOAT
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database initialization failed: {e}")

initialize_database()

# Create POST endpoint

@app.route("/api/measurements", methods = ["POST"])
def add_measurement():
    
    if not check_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    hostname = data.get("hostname")
    metric = data.get("metric")
    value = data.get("value")

    if not hostname or not metric or value is None:
        return jsonify({"error": "Missing 'hostname', 'metric', or 'value' field"}), 400
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO measurements (timestamp, hostname, metric, value) VALUES (GETDATE(), %s, %s, %s)",
            (hostname, metric, value)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "received", "hostname": hostname, "metric": metric, "value": value}), 201
    except Exception as e: 
        return jsonify({"error": str(e)}), 500
    
# Create the GET endpoint

@app.route("/api/measurements", methods = ["GET"])

def get_measurement():
    
    if not check_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    metric_filter = request.args.get("metric")
    hostname_filter = request.args.get("hostname")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT id, timestamp, hostname, metric, value FROM measurements"
        conditions = []
        params = []
        if metric_filter:
            conditions.append("metric = %s")
            params.append(metric_filter)
        if hostname_filter:
            conditions.append("hostname = %s")
            params.append(hostname_filter)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        results = [
            {
        "id": row[0],
        "timestamp": row[1].isoformat(),
        "hostname": row[2],
        "metric": row[3],
        "value": row[4]
            }
    for row in rows
]
        cursor.close()
        conn.close()
        return jsonify({"measurements": results}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 5000, debug = True)


