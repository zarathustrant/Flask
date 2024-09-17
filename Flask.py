from flask import Flask, request, jsonify

app = Flask(__name__)

# Store the latest location data
latest_location = {}

# Route to receive location data from the iOS app
@app.route('/api/location', methods=['POST'])
def receive_location():
    data = request.get_json()
    if 'latitude' in data and 'longitude' in data and 'timestamp' in data:
        global latest_location
        latest_location = data
        print(f"Received location: {latest_location}")
        return jsonify({"message": "Location received"}), 200
    else:
        return jsonify({"error": "Invalid data"}), 400

# Route to fetch the latest location for the dashboard
@app.route('/api/location', methods=['GET'])
def get_location():
    if latest_location:
        return jsonify(latest_location)
    else:
        return jsonify({"error": "No location data available"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)