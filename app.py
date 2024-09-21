from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pymongo import MongoClient
import json
from bson import ObjectId  # Import ObjectId to handle MongoDB _id

app = Flask(__name__)
CORS(app)

# MongoDB Atlas connection
client = MongoClient('mongodb+srv://zarathustrant:aCRmg2RAJcpoWMKo@aerys.lmphm.mongodb.net/?retryWrites=true&w=majority&appName=Aerys')
db = client['geojson_db']
layers_collection = db['layers']
styles_collection = db['styles']
map_view_collection = db['map_view']

@app.route('/')
def index():
    return send_file('index.html')

# Store the latest location data
latest_location = {}

# Route to receive location data from the iOS app
@app.route('/api/location', methods=['POST'])
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
        
@app.route('/update_map_view', methods=['POST'])
def update_map_view():
    try:
        data = request.json
        lat = data.get('lat')
        lng = data.get('lng')
        zoom = data.get('zoom')

        if not lat or not lng or not zoom:
            return jsonify({'error': 'Invalid data'}), 400

        existing_view = map_view_collection.find_one()
        if existing_view:
            map_view_collection.update_one({}, {'$set': {'lat': lat, 'lng': lng, 'zoom': zoom}})
        else:
            map_view_collection.insert_one({'lat': lat, 'lng': lng, 'zoom': zoom})

        return jsonify({'message': 'Map view updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_map_view', methods=['GET'])
def get_map_view():
    view = map_view_collection.find_one()
    if view:
        return jsonify({
            'lat': view.get('lat', 6),
            'lng': view.get('lng', 5),
            'zoom': view.get('zoom', 13)
        })
    else:
        return jsonify({'lat': 6, 'lng': 5, 'zoom': 13})

@app.route('/upload_geojson', methods=['POST'])
def upload_geojson():
    try:
        file = request.files['file']
        layer_name = request.form.get('layer_name')
        styles = json.loads(request.form.get('styles'))

        # Only accept valid GeoJSON files
        if not file.filename.endswith('.geojson'):
            return jsonify({'error': 'Invalid file format'}), 400

        geojson_data = json.load(file)

        layer_id = layers_collection.insert_one({
            'layer_name': layer_name,
            'geojson_data': geojson_data
        }).inserted_id

        styles_collection.insert_one({
            'layer_id': layer_id,
            'styles': styles
        })

        return jsonify({'message': 'Layer uploaded successfully', 'layer_id': str(layer_id)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_styles', methods=['PUT'])
def update_styles():
    try:
        data = request.json
        layer_id = data.get('layer_id')
        styles = data.get('styles')

        try:
            layer_id = ObjectId(layer_id)
        except Exception as e:
            return jsonify({'error': 'Invalid layer_id format'}), 400

        result = styles_collection.update_one(
            {'layer_id': layer_id},
            {'$set': {'styles': styles}}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'Layer not found'}), 404
        elif result.modified_count == 0:
            return jsonify({'message': 'No changes made to the styles'}), 200
        else:
            return jsonify({'message': 'Styles updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/layers', methods=['GET'])
def get_layers():
    try:
        layers = list(layers_collection.find())
        styles = list(styles_collection.find())

        combined = []
        for layer in layers:
            style = next((s for s in styles if str(s['layer_id']) == str(layer['_id'])), None)
            combined.append({
                'layer_id': str(layer['_id']),
                'layer_name': layer['layer_name'],
                'geojson_data': layer['geojson_data'],
                'styles': style['styles'] if style else {}
            })

        return jsonify(combined)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

