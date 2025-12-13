import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { Map as MapIcon, Calendar, Navigation, RefreshCw } from 'lucide-react';
import { endpoints } from '../../services/api';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icon in React Leaflet
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

interface LocationData {
    event_id: string;
    location_name: string;
    lat: number;
    lng: number;
    description: string;
}

// Component to update map view bounds
function MapUpdater({ locations }: { locations: LocationData[] }) {
    const map = useMap();
    useEffect(() => {
        if (locations.length > 0) {
            const bounds = L.latLngBounds(locations.map(l => [l.lat, l.lng]));
            map.fitBounds(bounds, { padding: [50, 50] });
        }
    }, [locations, map]);
    return null;
}

export function EvidenceMapModule() {
    const [locations, setLocations] = useState<LocationData[]>([]);
    const [loading, setLoading] = useState(false);
    const [analyzed, setAnalyzed] = useState(false);

    const handleAnalyze = async () => {
        setLoading(true);
        try {
            const response = await endpoints.evidenceMap.analyze('default_case');
            setLocations(response.data);
            setAnalyzed(true);
        } catch (error) {
            console.error("Failed to analyze locations:", error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full h-full flex flex-col p-8 text-halo-text overflow-hidden relative">
            {/* Header */}
            <div className="flex items-center justify-between mb-8 z-10 relative">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-halo-cyan/10 rounded-lg border border-halo-cyan/30 shadow-[0_0_15px_rgba(0,240,255,0.2)]">
                        <MapIcon className="text-halo-cyan w-8 h-8" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-light text-halo-text uppercase tracking-wider">Evidence Map</h2>
                        <p className="text-halo-muted text-sm">Geospatial reconstruction of timeline events</p>
                    </div>
                </div>
                <button
                    onClick={handleAnalyze}
                    disabled={loading}
                    className="flex items-center gap-2 px-6 py-3 bg-halo-cyan/10 border border-halo-cyan/50 rounded hover:bg-halo-cyan/20 text-halo-cyan transition-colors disabled:opacity-50 uppercase tracking-widest text-sm font-bold"
                >
                    {loading ? <RefreshCw className="animate-spin" size={18} /> : <Navigation size={18} />}
                    {analyzed ? 'Re-Analyze Locations' : 'Generate Map'}
                </button>
            </div>

            <div className="flex-1 halo-card p-1 overflow-hidden relative border-halo-cyan/30 bg-black/40">
                {!analyzed && !loading && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-black/80 backdrop-blur-sm">
                        <MapIcon size={64} className="text-halo-cyan/50 mb-4" />
                        <p className="text-halo-text text-lg font-light">Ready to extract geospatial data from your case.</p>
                        <p className="text-halo-muted text-sm mt-2">Click "Generate Map" to begin.</p>
                    </div>
                )}

                {loading && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-black/80 backdrop-blur-sm">
                        <RefreshCw size={64} className="text-halo-cyan animate-spin mb-4" />
                        <p className="text-halo-text text-lg font-light animate-pulse">Scanning documents for locations...</p>
                    </div>
                )}

                <MapContainer
                    center={[40.7128, -74.0060]}
                    zoom={13}
                    style={{ height: '100%', width: '100%', background: '#0a0a0a' }}
                    className="z-0"
                >
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    />

                    {locations.map((loc, i) => (
                        <Marker key={i} position={[loc.lat, loc.lng]}>
                            <Popup className="custom-popup">
                                <div className="p-2 min-w-[200px]">
                                    <h3 className="font-bold text-sm mb-1">{loc.location_name}</h3>
                                    <p className="text-xs text-gray-600 mb-2">{loc.description}</p>
                                    <div className="flex items-center gap-1 text-[10px] text-gray-400">
                                        <Calendar size={10} />
                                        <span>Event ID: {loc.event_id.substring(0, 8)}</span>
                                    </div>
                                </div>
                            </Popup>
                        </Marker>
                    ))}

                    <MapUpdater locations={locations} />
                </MapContainer>
            </div>

            {/* Stats Footer */}
            {analyzed && (
                <div className="absolute bottom-12 left-12 z-[1000] bg-black/80 border border-halo-cyan/30 rounded p-4 backdrop-blur-md">
                    <div className="flex items-center gap-4 text-xs font-mono text-halo-cyan">
                        <div>
                            <span className="block text-halo-muted text-[10px] uppercase">Locations Found</span>
                            <span className="text-lg font-bold">{locations.length}</span>
                        </div>
                        <div className="h-8 w-px bg-halo-border/30" />
                        <div>
                            <span className="block text-halo-muted text-[10px] uppercase">Region</span>
                            <span>Auto-Detected</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
