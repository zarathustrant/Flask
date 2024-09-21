from flask import Flask, request, jsonify, send_file
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

# Serve the index.html page for the Leaflet map
@app.route('/')
def index():
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

# Route to fetch and print GeoJSON file names
@app.route('/api/geojson_names', methods=['GET'])
def get_geojson_names():
    layers = list(layers_collection.find())
    
    layer_names = []
    for layer in layers:
        layer_name = layer.get('layer_name', 'Unnamed Layer')
        layer_names.append(layer_name)
        print(f"GeoJSON Layer Name: {layer_name}")

    return jsonify(layer_names), 200

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
# Route to update or store map view settings in MongoDB
@app.route('/update_map_view', methods=['POST'])
def update_map_view():
    data = request.json
    lat = data.get('lat')
    lng = data.get('lng')
    zoom = data.get('zoom')

    # Ensure lat, lng, and zoom are provided
    if lat is None or lng is None or zoom is None:
        return jsonify({'error': 'Invalid data'}), 400

    # Check if a map view document exists (you can customize the query if needed)
    existing_view = map_view_collection.find_one()

    if existing_view:
        # Update the existing document
        map_view_collection.update_one(
            {},  # Update the first document found (if you have multiple users, you can add user-specific queries)
            {'$set': {'lat': lat, 'lng': lng, 'zoom': zoom}}
        )
    else:
        # Insert a new document
        map_view_collection.insert_one({'lat': lat, 'lng': lng, 'zoom': zoom})

    return jsonify({'message': 'Map view updated successfully'}), 200

# Route to get the stored map view settings from MongoDB
@app.route('/get_map_view', methods=['GET'])
def get_map_view():
    view = map_view_collection.find_one()
    if view:
        return jsonify({
            'lat': view.get('lat', 6),  # Default lat if not found
            'lng': view.get('lng', 5),   # Default lng if not found
            'zoom': view.get('zoom', 13)     # Default zoom if not found
        })
    else:
        # Return default values if no map view is stored
        return jsonify({'lat': 6, 'lng': 5, 'zoom': 13})
    
    

# Other routes (upload_geojson, update_styles, get_layers) remain the same...
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

from bson import ObjectId  # Import ObjectId to handle MongoDB _id

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


