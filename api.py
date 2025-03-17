from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

@app.route('/ip_status')
def get_ip_status():
    conn = sqlite3.connect('ip_status.db')
    c = conn.cursor()
    c.execute("""
        SELECT file_name, ip_address, status
        FROM ip_status
        WHERE timestamp = (SELECT MAX(timestamp) FROM ip_status WHERE file_name = ip_status.file_name)
        ORDER BY file_name
    """)
    rows = c.fetchall()
    conn.close()

    result = [
        {"ASN": row[0], "IP": row[1], "Status": row[2]}
        for row in rows
    ]

    return jsonify(result)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
