var map;

function style(feature) {
    return {
        weight: 2,
        opacity: 1,
        color: '#000',
        fillOpacity: 0.5,
        fillColor: '#922'
    };
}

function initialize_map() {
    var layer = "toner-lite";
    map = new L.Map(layer, {
        //center: new L.LatLng(49.31838912886969, -94.919),
        zoom: 3,
        // Put attribution in text--it doesn't fit here
        attributionControl: false
    });
    var this_layer = new L.StamenTileLayer(layer);
    map.addLayer(this_layer);
}

function add_shape(data) {
  geojson_layer = L.geoJson(data, {style: style});
    geojson_layer.addTo(map);
    geojson_layer.bindPopup("test");
  map.fitBounds(geojson_layer.getBounds());
}