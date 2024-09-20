from flask import Flask, request, jsonify, send_file
import datetime
import os

app = Flask(__name__)

# Store the latest location data
latest_location = {}

# Root route to serve the Leaflet map (index.html in the root directory)
@app.route('/')
def index():
    # Serve the index.html file from the root directory
    return send_file('index.html')

# Route to receive location data from the iOS app (POST request)
@app.route('/api/location', methods=['POST'])
def receive_location():
    data = request.get_json()
    
    if 'latitude' in data and 'longitude' in data and 'timestamp' in data:
        # Convert Unix timestamp to human-readable format
        timestamp = data['timestamp']
        readable_time = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        # Update the latest location with the converted timestamp
        global latest_location
        latest_location = {
            'latitude': data['latitude'],
            'longitude': data['longitude'],
            'timestamp': data['timestamp'],  # Original timestamp
            'readable_time': readable_time   # Human-readable timestamp
        }
        
        print(f"Received location: {latest_location}")
        return jsonify({"message": "Location received", "readable_time": readable_time}), 200
    else:
        return jsonify({"error": "Invalid data"}), 400

# Route to fetch the latest location for the dashboard (GET request)
@app.route('/api/location', methods=['GET'])
def get_location():
    if latest_location:
        return jsonify(latest_location)
    else:
        return jsonify({"error": "No location data available"}), 404
