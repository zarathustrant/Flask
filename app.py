from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
import json
import datetime
import os
from bson import ObjectId

app = Flask(__name__)
CORS(app)

# MongoDB Atlas connection
client = MongoClient('mongodb+srv://zarathustrant:aCRmg2RAJcpoWMKo@aerys.lmphm.mongodb.net/?retryWrites=true&w=majority&appName=Aerys')
db = client['geojson_db']  # Replace with your database name
layers_collection = db['layers']
styles_collection = db['styles']
map_view_collection = db['map_view']

# ======================== LOCATION MANAGER ========================= #

# Store the latest location data
latest_location = {}

# Serve the index.html page with the latest location and GeoJSON layers
@app.route('/')
def index():
    # Fetch all layers and their GeoJSON data
    layers = list(layers_collection.find())
    
    # Fetch the latest location
    location = latest_location if latest_location else {'latitude': 6, 'longitude': 5}
    
    # Prepare the GeoJSON data to pass to the template
    geojson_layers = []
    for layer in layers:
        geojson_layers.append({
            'layer_name': layer['layer_name'],
            'geojson_data': layer['geojson_data']
        })
    
    # Render the template and pass the data (latest location and GeoJSON layers)
    return render_template('index.html', location=location, geojson_layers=geojson_layers)

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

# ======================== END OF LOCATION MANAGER ========================= #


# ======================== GEOJSON LAYER MANAGEMENT ========================= #

# Route to fetch all GeoJSON layers
@app.route('/layers', methods=['GET'])
def get_layers():
    # Fetch all layers and styles
    layers = list(layers_collection.find())
    styles = list(styles_collection.find())

    combined = []
    for layer in layers:
        style = next((s for s in styles if str(s['layer_id']) == str(layer['_id'])), None)
        combined.append({
            'layer_id': str(layer['_id']),  # Include _id from layers_collection as layer_id
            'layer_name': layer['layer_name'],
            'geojson_data': layer['geojson_data'],
            'styles': style['styles'] if style else {}
        })

    return jsonify(combined)

# Route to fetch a specific GeoJSON layer by layer_id
@app.route('/layers/<layer_id>', methods=['GET'])
def get_layer(layer_id):
    try:
        layer_id = ObjectId(layer_id)  # Convert to ObjectId
    except Exception as e:
        return jsonify({'error': 'Invalid layer_id format'}), 400

    # Fetch the GeoJSON layer
    layer = layers_collection.find_one({'_id': layer_id})
    if layer:
        return jsonify({
            'layer_id': str(layer['_id']),
            'layer_name': layer['layer_name'],
            'geojson_data': layer['geojson_data']
        })
    else:
        return jsonify({'error': 'Layer not found'}), 404

# Route to upload a new GeoJSON layer with styles
@app.route('/upload_geojson', methods=['POST'])
def upload_geojson():
    file = request.files['file']
    layer_name = request.form.get('layer_name')
    styles = json.loads(request.form.get('styles'))  # Styles sent as JSON

    # Parse GeoJSON data
    geojson_data = json.load(file)

    # Save GeoJSON and styles to MongoDB
    layer_id = layers_collection.insert_one({
        'layer_name': layer_name,
        'geojson_data': geojson_data
    }).inserted_id

    styles_collection.insert_one({
        'layer_id': layer_id,
        'styles': styles
    })

    return jsonify({'message': 'Layer uploaded successfully', 'layer_id': str(layer_id)})

# Route to update the styles of a specific GeoJSON layer
@app.route('/update_styles', methods=['PUT'])
def update_styles():
    data = request.json
    layer_id = data.get('layer_id')
    styles = data.get('styles')

    # Convert layer_id to ObjectId if it's a valid ObjectId
    try:
        layer_id = ObjectId(layer_id)
    except Exception as e:
        return jsonify({'error': 'Invalid layer_id format'}), 400

    # Update styles in MongoDB
    result = styles_collection.update_one(
        {'layer_id': layer_id},
        {'$set': {'styles': styles}}
    )

    # Check if the document was modified
    if result.matched_count == 0:
        return jsonify({'error': 'Layer not found'}), 404
    elif result.modified_count == 0:
        return jsonify({'message': 'No changes made to the styles'}), 200
    else:
        return jsonify({'message': 'Styles updated successfully'}), 200

# Route to update attributes (fields) of a specific GeoJSON layer
@app.route('/layers/<layer_id>/update_attributes', methods=['PUT'])
def update_layer_attributes(layer_id):
    try:
        layer_id = ObjectId(layer_id)  # Convert to ObjectId
    except Exception as e:
        return jsonify({'error': 'Invalid layer_id format'}), 400

    data = request.json
    updated_attributes = data.get('updated_attributes')

    if not updated_attributes:
        return jsonify({'error': 'No attributes to update'}), 400

    # Update the layer's GeoJSON data attributes
    result = layers_collection.update_one(
        {'_id': layer_id, 'geojson_data.features': {'$exists': True}},  # Ensure we only update layers with features
        {'$set': {'geojson_data.features.$[].properties': updated_attributes}}  # Update all feature properties
    )

    if result.matched_count == 0:
        return jsonify({'error': 'Layer not found'}), 404
    elif result.modified_count == 0:
        return jsonify({'message': 'No changes made to the attributes'}), 200
    else:
        return jsonify({'message': 'Layer attributes updated successfully'}), 200

