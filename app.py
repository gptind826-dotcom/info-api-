import os
import socket
import urllib.request
from pathlib import Path
from flask import Flask, jsonify
from flask_caching import Cache
import ipaddress
import requests

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 86400})

# Configuration
TELEGRAM_LINK = "https://t.me/exucodex"

# Database configuration
DATABASE_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"
DATABASE_FILE = "GeoLite2-City.mmdb"

def download_database():
    """Download MaxMind database if not exists"""
    if Path(DATABASE_FILE).exists():
        print(f"✓ Database already exists: {DATABASE_FILE}")
        return True
    
    print(f"⬇ Downloading database...")
    try:
        urllib.request.urlretrieve(DATABASE_URL, DATABASE_FILE)
        print(f"✓ Database downloaded successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to download database: {e}")
        return False

# Download database on startup
download_database()

# Initialize database reader
reader = None
try:
    import geoip2.database
    if Path(DATABASE_FILE).exists():
        reader = geoip2.database.Reader(DATABASE_FILE)
        print("✓ MaxMind database loaded successfully")
except ImportError:
    print("⚠ geoip2 not installed - run: pip install geoip2")
except Exception as e:
    print(f"⚠ Database load failed: {e}")

def is_valid_ip(ip_string):
    """Check if string is a valid IP address"""
    try:
        ipaddress.ip_address(ip_string)
        return True
    except:
        return False

def resolve_domain(domain):
    """Resolve domain name to IP address"""
    try:
        return socket.gethostbyname(domain)
    except:
        return None

def get_hostname(ip):
    """Get reverse DNS hostname"""
    try:
        return socket.gethostbyaddr(ip)[0]
    except:
        return ""

def get_anycast(ip):
    """Detect anycast IP"""
    anycast_ips = {
        '8.8.8.8': True, '8.8.4.4': True,
        '1.1.1.1': True, '1.0.0.1': True,
        '9.9.9.9': True, '149.112.112.112': True,
        '208.67.222.222': True, '208.67.220.220': True
    }
    return anycast_ips.get(ip, False)

def get_from_database(ip):
    """Get info from local database"""
    if not reader:
        return None
    
    try:
        response = reader.city(ip)
        return {
            "city": response.city.name or "",
            "region": response.subdivisions.most_specific.iso_code if response.subdivisions.most_specific else "",
            "country": response.country.iso_code or "",
            "loc": f"{response.location.latitude},{response.location.longitude}" if response.location.latitude else "",
            "postal": response.postal.code or "",
            "timezone": response.location.time_zone or ""
        }
    except:
        return None

def get_from_api(ip):
    """Get ALL info from ip-api.com"""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
        data = response.json()
        
        if data.get('status') == 'success':
            return {
                "city": data.get('city', ''),
                "region": data.get('regionName', ''),
                "country": data.get('countryCode', ''),
                "loc": f"{data.get('lat', '')},{data.get('lon', '')}",
                "postal": data.get('zip', ''),
                "timezone": data.get('timezone', ''),
                "org": data.get('org', 'Unknown Organization')
            }
    except Exception as e:
        print(f"API fetch failed: {e}")
    
    return None

def check_missing_fields(data):
    """Check which fields are missing or empty"""
    required_fields = ['city', 'region', 'country', 'loc', 'postal', 'timezone']
    missing = []
    
    for field in required_fields:
        if not data.get(field):  # Empty string or None
            missing.append(field)
    
    return missing

@app.route('/<query>/json')
@cache.cached(timeout=86400)
def ip_info(query):
    """Main API - fills missing fields automatically"""
    
    # Check if query is IP or domain
    if is_valid_ip(query):
        ip = query
        hostname = get_hostname(ip)
    else:
        # It's a domain, resolve it
        resolved_ip = resolve_domain(query)
        if not resolved_ip:
            return jsonify({
                "error": f"Could not resolve domain: {query}",
                "telegram": TELEGRAM_LINK
            }), 404
        ip = resolved_ip
        hostname = query  # Domain name as hostname
    
    # Step 1: Try to get data from database
    db_data = get_from_database(ip)
    
    # Step 2: Prepare initial response
    if db_data:
        # Database has some data
        result = {
            "ip": ip,
            "hostname": hostname,
            "city": db_data.get('city', ''),
            "region": db_data.get('region', ''),
            "country": db_data.get('country', ''),
            "loc": db_data.get('loc', ''),
            "org": "",  # Will be filled from API
            "postal": db_data.get('postal', ''),
            "timezone": db_data.get('timezone', ''),
            "telegram": TELEGRAM_LINK,
            "anycast": get_anycast(ip)
        }
        
        # Step 3: Check for missing fields
        missing_fields = check_missing_fields(result)
        
        if missing_fields:
            print(f"⚠ Missing fields for {ip}: {missing_fields}")
            print(f"🔄 Fetching from API to fill missing data...")
            
            # Step 4: Get data from API to fill missing fields
            api_data = get_from_api(ip)
            
            if api_data:
                # Fill only the missing fields
                for field in missing_fields:
                    if field in api_data and api_data[field]:
                        result[field] = api_data[field]
                        print(f"✓ Filled {field}: {api_data[field]}")
                
                # Always get organization from API (database doesn't have it)
                if api_data.get('org'):
                    result['org'] = api_data['org']
                    print(f"✓ Filled org: {api_data['org']}")
        else:
            print(f"✓ Database has complete data for {ip}")
            # Still need org from API
            api_data = get_from_api(ip)
            if api_data and api_data.get('org'):
                result['org'] = api_data['org']
        
        return jsonify(result)
    
    # Step 5: Database has NO data at all - use API completely
    print(f"⚠ No database data for {ip}, using API only")
    api_data = get_from_api(ip)
    
    if api_data:
        result = {
            "ip": ip,
            "hostname": hostname,
            "city": api_data.get('city', ''),
            "region": api_data.get('region', ''),
            "country": api_data.get('country', ''),
            "loc": api_data.get('loc', ''),
            "org": api_data.get('org', 'Unknown Organization'),
            "postal": api_data.get('postal', ''),
            "timezone": api_data.get('timezone', ''),
            "telegram": TELEGRAM_LINK,
            "anycast": get_anycast(ip)
        }
        return jsonify(result)
    
    # Step 6: Everything failed
    return jsonify({
        "ip": ip,
        "hostname": hostname,
        "city": "",
        "region": "",
        "country": "Unknown",
        "loc": "",
        "org": "Unknown Organization",
        "postal": "",
        "timezone": "",
        "telegram": TELEGRAM_LINK,
        "anycast": get_anycast(ip)
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "database_loaded": reader is not None,
        "telegram": TELEGRAM_LINK,
        "port": 8080
    })

@app.route('/')
def home():
    return jsonify({
        "name": "IP Geolocation API",
        "version": "4.0",
        "features": [
            "Database first (fast)",
            "Auto-detects missing fields",
            "Fills missing data from API",
            "Works with IPs and domains"
        ],
        "example": "http://localhost:8080/8.8.8.8/json",
        "telegram": TELEGRAM_LINK
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 IP Geolocation API Server v4.0")
    print("="*60)
    print(f"📱 Telegram: {TELEGRAM_LINK}")
    print(f"💾 Database: {DATABASE_FILE}")
    print(f"🔄 Strategy: Database → Check missing → API fill")
    print(f"🌐 Server: http://localhost:8080")
    print(f"🔍 Test IP: http://localhost:8080/8.8.8.8/json")
    print(f"🔍 Test Domain: http://localhost:8080/google.com/json")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=8080, debug=False)
