

// Initialize the map
var map = L.map('map', {
    zoomControl: false,  // Disable default zoom control
    scrollWheelZoom: true,  // Enable zoom with scroll wheel
    dragging: true  // Enable map dragging
}).setView([localStorage.getItem('defaultLat') || 6, localStorage.getItem('defaultLng') || 5], localStorage.getItem('defaultZoom') || 4);

// Base Layers
var watercolor = L.tileLayer('https://tiles.stadiamaps.com/tiles/stamen_watercolor/{z}/{x}/{y}.{ext}', {
    minZoom: 1,
    maxZoom: 16,
    attribution: '&copy; <a href="https://www.stadiamaps.com/" target="_blank">Stadia Maps</a> &copy; <a href="https://www.stamen.com/" target="_blank">Stamen Design</a>',
    ext: 'jpg'
});

var googleSatHybrid = L.tileLayer('https://{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
    attribution: '&copy; <a href="https://www.google.com/earth/">Google Earth</a>',
    subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
    maxZoom: 19
});

var TopPlusOpen_Color = L.tileLayer('http://sgx.geodatenzentrum.de/wmts_topplus_open/tile/1.0.0/web/default/WEBMERCATOR/{z}/{y}/{x}.png', {
    maxZoom: 18,
    attribution: 'Map data: &copy; <a href="http://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>'
});

// Load the last selected basemap from localStorage
var lastSelectedBasemap = localStorage.getItem('selectedBasemap');
switch (lastSelectedBasemap) {
    case 'watercolor': watercolor.addTo(map); break;
    case 'googleSatHybrid': googleSatHybrid.addTo(map); break;
    case 'TopPlusOpen_Color': TopPlusOpen_Color.addTo(map); break;
    default: googleSatHybrid.addTo(map);  // Default basemap
}

// Layer switch logic
document.getElementById('switch-to-watercolor').addEventListener('click', () => switchBaseLayer(watercolor, 'watercolor'));
document.getElementById('switch-to-google').addEventListener('click', () => switchBaseLayer(googleSatHybrid, 'googleSatHybrid'));
document.getElementById('switch-to-TopPlus').addEventListener('click', () => switchBaseLayer(TopPlusOpen_Color, 'TopPlusOpen_Color'));

function switchBaseLayer(layer, layerName) {
    map.eachLayer((l) => map.removeLayer(l));  // Remove existing layers
    layer.addTo(map);  // Add the selected layer
    localStorage.setItem('selectedBasemap', layerName);  // Save basemap choice to localStorage
}

// Handle default view settings
document.getElementById('setViewBtn').addEventListener('click', () => {
    var lat = parseFloat(document.getElementById('latInput').value);
    var lng = parseFloat(document.getElementById('lngInput').value);
    var zoom = parseInt(document.getElementById('zoomInput').value);

    if (!isNaN(lat) && !isNaN(lng) && !isNaN(zoom)) {
        map.setView([lat, lng], zoom);
        localStorage.setItem('defaultLat', lat);
        localStorage.setItem('defaultLng', lng);
        localStorage.setItem('defaultZoom', zoom);
        alert('View settings saved!');
    } else {
        alert('Please enter valid numbers.');
    }
});

// Zoom control buttons
document.getElementById('zoom-in').addEventListener('click', () => map.zoomIn());
document.getElementById('zoom-out').addEventListener('click', () => map.zoomOut());

// Reset view to default settings
document.getElementById('home').addEventListener('click', () => {
    var defaultLat = localStorage.getItem('defaultLat') || 6;
    var defaultLng = localStorage.getItem('defaultLng') || 5;
    var defaultZoom = localStorage.getItem('defaultZoom') || 4;
    map.setView([defaultLat, defaultLng], defaultZoom);
});

// Display current zoom level
var zoomLevelDisplay = document.getElementById('zoom-level');
zoomLevelDisplay.innerHTML = 'Zoom: ' + map.getZoom();
map.on('zoomend', () => zoomLevelDisplay.innerHTML = 'Zoom Level: ' + map.getZoom());

// Mouse position display
map.on('mousemove', (e) => {
    document.getElementById('mouse-position').innerHTML = `Lat: ${e.latlng.lat.toFixed(5)}, Lng: ${e.latlng.lng.toFixed(5)}`;
});


let currentLayerId = null;
let currentLayer = null;

// Function to add layers to the map and display the layer name in the list
function addLayerToMap(layerData) {
    const geoLayer = L.geoJSON(layerData.geojson_data, {
        style: layerData.styles
    }).addTo(map);

    // Add the layer name to the list
    const listItem = document.createElement('li');
    listItem.className = 'list-group-item';
    listItem.textContent = layerData.layer_name;

    // Click event for list item to open the style editing modal
    listItem.onclick = function() {
        currentLayerId = layerData.layer_id;
        currentLayer = geoLayer;
        $('#styleModal').modal('show');
    };

    document.getElementById('layersList').appendChild(listItem);
}

// Load layers from the backend
function loadLayers() {
    fetch('http://127.0.0.1:5000/layers')
        .then(response => response.json())
        .then(layers => {
            layers.forEach(layer => {
                addLayerToMap(layer);
            });
        });
}

// Handle uploading a new GeoJSON file
document.getElementById('uploadBtn').addEventListener('click', () => {
    document.getElementById('geojsonFile').click();
});

document.getElementById('geojsonFile').addEventListener('change', function () {
    const file = this.files[0];
    if (file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('layer_name', file.name);

        // Default styles for the new layer
        const styles = {
            fillColor: '#ff7800',
            weight: 2,
            color: '#000000',
        };
        formData.append('styles', JSON.stringify(styles));

        // Upload GeoJSON to the server
        fetch('http://127.0.0.1:5000/upload_geojson', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            console.log(data.message);
            loadLayers();  // Reload layers after upload
        });
    }
});

// Handle saving styles
document.getElementById('saveStylesBtn').addEventListener('click', () => {
    const fillColor = document.getElementById('fillColor').value;
    const strokeColor = document.getElementById('strokeColor').value;
    const weight = document.getElementById('weight').value;

    const newStyles = {
        fillColor: fillColor,
        color: strokeColor,
        weight: parseInt(weight),
    };

    // Update styles on the server
    fetch('http://127.0.0.1:5000/update_styles', {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            layer_id: currentLayerId,
            styles: newStyles
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data.message);

        // Update the styles on the map
        currentLayer.setStyle(newStyles);

        // Close the modal
        $('#styleModal').modal('hide');
    });
});



// Modal triggers
$('#open-generateSrtmDataModal').on('click', () => $('#generateSrtmDataModal').modal('show'));
$('#open-convertKmlModal').on('click', () => $('#convertKmlModal').modal('show'));
$('#open-convertCoordinatesModal').on('click', () => $('#convertCoordinatesModal').modal('show'));
$('#open-cogoModal').on('click', () => $('#cogoModal').modal('show'));
$('#open-createPolygonsModal').on('click', () => $('#createPolygonsModal').modal('show'));
$('#addTextWidget').on('click', () => $('#addTextWidgetModal').modal('show'));

// Toggle control visibility
$('#analysisIcon').on('click', () => $('#analysisControls').toggleClass('d-none'));
$('#settingsIcon').on('click', () => $('#settingsControls').toggleClass('d-none'));
$('#layerIcon').on('click', () => $('#layersControls').toggleClass('d-none'));

// Initial load of layers
loadLayers();