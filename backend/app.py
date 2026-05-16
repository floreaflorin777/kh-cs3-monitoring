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
    
    metric = data.get("metric")
    value = data.get("value")

    if not metric or value is None:
        return jsonify({"error": "Missing 'metric' or 'value' field"}), 400
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO measurements (timestamp, metric, value) VALUES (GETDATE(), %s, %s)",
            (metric, value)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "received", "metric": metric, "value": value}), 201
    except Exception as e: 
        return jsonify({"error": str(e)}), 500
    
# Create the GET endpoint

@app.route("/api/measurements", methods = ["GET"])

def get_measurement():
    
    if not check_api_key():
        return jsonify({"error": "Unauthorized"}), 401
    
    metric_filter = request.args.get("metric")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if metric_filter:
            cursor.execute(
                "SELECT id, timestamp, metric, value FROM measurements WHERE metric = %s ORDER BY timestamp DESC",
                (metric_filter,)
            )
        else:
            cursor.execute(
                "SELECT id, timestamp, metric, value FROM measurements ORDER BY timestamp DESC"
            )
        rows = cursor.fetchall()
        results = [
    {
        "id": row[0],
        "timestamp": row[1].isoformat(),
        "metric": row[2],
        "value": row[3]
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


