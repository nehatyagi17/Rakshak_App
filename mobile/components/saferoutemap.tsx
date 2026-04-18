import React, { useState, useRef } from 'react';
import { 
  View, Text, StyleSheet, TouchableOpacity, TextInput, 
  FlatList, Alert, ActivityIndicator, Keyboard, Dimensions
} from 'react-native';
import { WebView } from 'react-native-webview';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import axios from 'axios';
import * as Location from 'expo-location';

const { width } = Dimensions.get('window');

interface SafeRouteMapProps {
  authToken: string;
  apiBase: string;
  onBack: () => void;
  theme: any;
}

const UTTARAKHAND_BBOX = [77.57, 28.71, 81.04, 31.45]; // [minLng, minLat, maxLng, maxLat]

export const SafeRouteMap: React.FC<SafeRouteMapProps> = ({ authToken, apiBase, onBack, theme }) => {
  const [source, setSource] = useState('');
  const [dest, setDest] = useState('');
  const [sourceCoords, setSourceCoords] = useState<{lat: number, lng: number} | null>(null);
  const [destCoords, setDestCoords] = useState<{lat: number, lng: number} | null>(null);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [activeField, setActiveField] = useState<'source' | 'dest' | null>(null);
  const [loading, setLoading] = useState(false);
  const webViewRef = useRef<WebView>(null);
  const searchTimer = useRef<NodeJS.Timeout | null>(null);

  // Leaflet HTML Template
  const leafletHTML = [
    '<!DOCTYPE html>',
    '<html>',
    '<head>',
    '  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />',
    '  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />',
    '  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>',
    '  <style>',
    '    body { margin: 0; padding: 0; background: #000; }',
    '    #map { height: 100vh; width: 100vw; }',
    '    .leaflet-container { background: #0A0E17 !important; }',
    '  </style>',
    '</head>',
    '<body>',
    '  <div id="map"></div>',
    '  <script>',
    '    const map = L.map("map", { zoomControl: false, attributionControl: false }).setView([30.3165, 78.0322], 13);',
    '    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {',
    '      maxZoom: 19,',
    '      attribution: "&copy; <a href=\'https://www.openstreetmap.org/copyright\'>OpenStreetMap</a> contributors &copy; <a href=\'https://carto.com/attributions\'>CARTO</a>"',
    '    }).addTo(map);',
    '    let sourceMarker, destMarker, routeLayer;',
    '    window.updateMarkers = (s, d) => {',
    '      if (sourceMarker) map.removeLayer(sourceMarker);',
    '      if (destMarker) map.removeLayer(destMarker);',
    '      if (s) { sourceMarker = L.circleMarker([s.lat, s.lng], { color: "' + theme.primary + '", radius: 8, fillOpacity: 1 }).addTo(map); }',
    '      if (d) { destMarker = L.marker([d.lat, d.lng]).addTo(map); }',
    '      if (s && !d) map.flyTo([s.lat, s.lng], 15);',
    '    };',
    '    window.drawRoute = (geometry) => {',
    '      if (routeLayer) map.removeLayer(routeLayer);',
    '      routeLayer = L.geoJSON(geometry, { style: { color: "#3B82F6", weight: 6, opacity: 0.8, lineJoin: "round" } }).addTo(map);',
    '      map.fitBounds(routeLayer.getBounds(), { padding: [50, 50] });',
    '    };',
    '  </script>',
    '</body>',
    '</html>'
  ].join('\n');

  const fetchSuggestions = async (text: string) => {
    if (text.length < 3) {
      setSuggestions([]);
      return;
    }
    try {
      const resp = await axios.get('https://nominatim.openstreetmap.org/search', {
        headers: { 'User-Agent': 'RakshakApp/1.0' },
        params: {
          q: text,
          format: 'json',
          addressdetails: 1,
          limit: 5,
          viewbox: UTTARAKHAND_BBOX.join(','),
          bounded: 1,
          countrycodes: 'in'
        }
      });
      setSuggestions(resp.data);
    } catch (e) {
      console.warn("Geocoding error", e);
    }
  };

  const handleSelectSuggestion = (item: any) => {
    const coords = { lat: parseFloat(item.lat), lng: parseFloat(item.lon) };
    if (activeField === 'source') {
      setSource(item.display_name);
      setSourceCoords(coords);
      const js = 'updateMarkers(' + JSON.stringify(coords) + ', ' + JSON.stringify(destCoords) + ')';
      webViewRef.current?.injectJavaScript(js);
    } else {
      setDest(item.display_name);
      setDestCoords(coords);
      const js = 'updateMarkers(' + JSON.stringify(sourceCoords) + ', ' + JSON.stringify(coords) + ')';
      webViewRef.current?.injectJavaScript(js);
    }
    setSuggestions([]);
    setActiveField(null);
    Keyboard.dismiss();
  };

  const useCurrentLocation = async () => {
    setLoading(true);
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Denied', 'Location permission is required.');
        return;
      }
      const location = await Location.getCurrentPositionAsync({});
      const coords = { lat: location.coords.latitude, lng: location.coords.longitude };
      
      if (coords.lat < UTTARAKHAND_BBOX[1] || coords.lat > UTTARAKHAND_BBOX[3] ||
          coords.lng < UTTARAKHAND_BBOX[0] || coords.lng > UTTARAKHAND_BBOX[2]) {
        Alert.alert("Out of Bounds", "RAKSHAK Routing is currently optimized for Uttarakhand region only.");
        return;
      }

      setSource('Current Location');
      setSourceCoords(coords);
      const js = 'updateMarkers(' + JSON.stringify(coords) + ', ' + JSON.stringify(destCoords) + ')';
      webViewRef.current?.injectJavaScript(js);
    } catch (e) {
      Alert.alert('Error', 'Could not get device location.');
    } finally {
      setLoading(false);
    }
  };

  const findPath = async () => {
    if (!sourceCoords || !destCoords) {
      Alert.alert("Missing Locations", "Please select both starting and destination points.");
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post(apiBase + '/alerts/route/', {
        src_lat: sourceCoords.lat,
        src_lng: sourceCoords.lng,
        dest_lat: destCoords.lat,
        dest_lng: destCoords.lng
      }, {
        headers: { Authorization: 'Bearer ' + authToken }
      });

      if (res.data.geometry) {
        const js = 'drawRoute(' + JSON.stringify(res.data.geometry) + ')';
        webViewRef.current?.injectJavaScript(js);
      }
    } catch (e: any) {
      Alert.alert("Routing Error", e.response?.data?.error || "Could not calculate route.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backBtn}>
          <MaterialCommunityIcons name="arrow-left" color="#FFF" size={24} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Safe Route Navigator</Text>
      </View>

      <View style={styles.mapContainer}>
        <WebView 
          ref={webViewRef}
          source={{ html: leafletHTML }}
          style={{ flex: 1 }}
          originWhitelist={['*']}
          javaScriptEnabled={true}
          domStorageEnabled={true}
        />
        
        {/* --- UI OVERLAY AT TOP --- */}
        <View style={styles.uiOverlay}>
          <View style={styles.inputContainer}>
            <View style={styles.inputGroup}>
              <View style={styles.inputWrapper}>
                <MaterialCommunityIcons name="circle-slice-8" color={theme.primary} size={18} />
                <TextInput 
                  style={styles.input}
                  placeholder="Starting Location..."
                  placeholderTextColor="#666"
                  value={source}
                  onChangeText={(t) => {
                    setSource(t);
                    setActiveField('source');
                    if (searchTimer.current) clearTimeout(searchTimer.current);
                    searchTimer.current = setTimeout(() => fetchSuggestions(t), 500);
                  }}
                  onFocus={() => setActiveField('source')}
                />
                <TouchableOpacity onPress={useCurrentLocation} style={styles.locBtn}>
                  <MaterialCommunityIcons name="crosshairs-gps" color={theme.primary} size={20} />
                </TouchableOpacity>
              </View>

              <View style={[styles.inputWrapper, { marginTop: 10 }]}>
                <MaterialCommunityIcons name="map-marker" color={theme.warning} size={18} />
                <TextInput 
                  style={styles.input}
                  placeholder="Destination..."
                  placeholderTextColor="#666"
                  value={dest}
                  onChangeText={(t) => {
                    setDest(t);
                    setActiveField('dest');
                    if (searchTimer.current) clearTimeout(searchTimer.current);
                    searchTimer.current = setTimeout(() => fetchSuggestions(t), 500);
                  }}
                  onFocus={() => setActiveField('dest')}
                />
              </View>
            </View>

            {suggestions.length > 0 && activeField && (
              <View style={styles.suggestionBox}>
                <FlatList 
                  data={suggestions}
                  keyExtractor={(item, index) => index.toString()}
                  renderItem={({ item }) => (
                    <TouchableOpacity 
                      style={styles.suggestionItem}
                      onPress={() => handleSelectSuggestion(item)}
                    >
                      <MaterialCommunityIcons name="history" color="#888" size={16} />
                      <Text style={styles.suggestionText} numberOfLines={1}>{item.display_name}</Text>
                    </TouchableOpacity>
                  )}
                />
              </View>
            )}

            <TouchableOpacity 
              style={[styles.findBtn, loading && styles.btnDisabled]} 
              onPress={findPath}
              disabled={loading}
            >
              {loading ? <ActivityIndicator color="#FFF" /> : (
                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                  <MaterialCommunityIcons name="navigation-variant" color="#FFF" size={20} />
                  <Text style={styles.findBtnText}>FIND SAFE ROUTE</Text>
                </View>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  header: { 
    height: 100, 
    paddingTop: 50, 
    flexDirection: 'row', 
    alignItems: 'center', 
    paddingHorizontal: 20, 
    backgroundColor: '#0A0E17',
    zIndex: 100 
  },
  backBtn: { padding: 8, marginRight: 15 },
  headerTitle: { color: '#FFF', fontSize: 20, fontWeight: 'bold', letterSpacing: 1 },
  mapContainer: { flex: 1 },
  uiOverlay: {
    position: 'absolute',
    top: 0,
    width: '100%',
    padding: 20,
    backgroundColor: 'rgba(10, 14, 23, 0.95)',
    borderBottomLeftRadius: 30,
    borderBottomRightRadius: 30,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.05)',
    zIndex: 1000,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.5,
    shadowRadius: 15,
    elevation: 10
  },
  inputContainer: { width: '100%' },
  inputGroup: { backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: 20, padding: 15 },
  inputWrapper: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    backgroundColor: 'rgba(0,0,0,0.5)', 
    borderRadius: 12, 
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)'
  },
  input: { flex: 1, color: '#FFF', fontSize: 14, paddingVertical: 12, marginLeft: 10 },
  locBtn: { padding: 5 },
  findBtn: { 
    backgroundColor: '#7C3AED', 
    marginTop: 20, 
    borderRadius: 15, 
    paddingVertical: 18, 
    justifyContent: 'center', 
    alignItems: 'center' ,
    shadowColor: '#7C3AED',
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.3,
    shadowRadius: 10
  },
  btnDisabled: { opacity: 0.6 },
  findBtnText: { color: '#FFF', fontWeight: 'bold', letterSpacing: 2, marginLeft: 10 },
  suggestionBox: { 
    backgroundColor: '#111827', 
    borderRadius: 15, 
    marginTop: 10, 
    maxHeight: 200, 
    borderWidth: 1, 
    borderColor: 'rgba(255,255,255,0.1)',
    overflow: 'hidden'
  },
  suggestionItem: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    padding: 15, 
    borderBottomWidth: 1, 
    borderBottomColor: 'rgba(255,255,255,0.05)' 
  },
  suggestionText: { color: '#CCC', fontSize: 13, marginLeft: 10, flex: 1 },
});
