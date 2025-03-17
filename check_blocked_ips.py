
from prometheus_client import start_http_server, Gauge
import requests
import ipaddress
import sqlite3
import time
from datetime import datetime

TRUSTPOSITIF_URL = "https://raw.githubusercontent.com/alsyundawy/TrustPositif/main/ipaddress_isp"

COMPANY_IP_FILES = ["IDCH-AS136052.txt", "CLOUDHOST-AS138608.txt", "AWANKILAT-AS138062.txt"]

blocked_ips_count = Gauge('blocked_ip_count', 'Number of blocked IP /32', ['file'])
not_blocked_ips_count = Gauge('not_blocked_ip_count', 'Number of not blocked IP /32', ['file'])

def init_db():
    conn = sqlite3.connect('ip_status.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ip_status
                 (timestamp TEXT, file_name TEXT, ip_address TEXT, status TEXT)''')
    conn.commit()
    conn.close()

def get_trustpositif_ips():
    try:
        response = requests.get(TRUSTPOSITIF_URL)
        response.raise_for_status()
        return set(response.text.splitlines())
    except requests.RequestException as e:
        print(f"Error fetching TrustPositif list: {e}")
        return set()

def read_company_networks(file_path):
    networks = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    networks.append(ipaddress.ip_network(line, strict=False))
        return networks
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

def save_to_db(timestamp, file_name, ip_address, status):
    conn = sqlite3.connect('ip_status.db')
    c = conn.cursor()
    c.execute("INSERT INTO ip_status (timestamp, file_name, ip_address, status) VALUES (?, ?, ?, ?)",
              (timestamp, file_name, str(ip_address), status))
    conn.commit()
    conn.close()

def count_total_ips(networks):
    return sum(2** (32 - network.prefixlen) for network in networks)

def check_blocked_ips():
    trustpositif_ips = get_trustpositif_ips()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for file in COMPANY_IP_FILES:
        company_networks = read_company_networks(file)
        blocked_ips = set()

        for ip in trustpositif_ips:
            try:
                ip_addr = ipaddress.ip_address(ip)
                for network in company_networks:
                    if ip_addr in network:
                        blocked_ips.add(str(ip_addr) + "/32")
                        file_asn = file.split('-')[1].replace('.txt', '')
                        save_to_db(timestamp, file_asn, str(ip_addr) + "/32", "Blocked")
                        break
            except ValueError:
                continue

        
        total_ips = count_total_ips(company_networks)
        blocked_count = len(blocked_ips)
        not_blocked_count = total_ips - blocked_count  
        
        file_asn = file.split('-')[1].replace('.txt', '')
        blocked_ips_count.labels(file=file_asn).set(blocked_count)
        not_blocked_ips_count.labels(file=file_asn).set(not_blocked_count)
        print(f"Updated metrics for {file_asn}: Blocked={blocked_count}, Not Blocked={not_blocked_count}")

if __name__ == "__main__":
    init_db()  
    start_http_server(8000)  
    print("Prometheus metrics available at http://0.0.0.0:8000")

    while True:
        check_blocked_ips()
