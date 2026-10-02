'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Search, Navigation, MapPin, Loader2, CheckCircle2, Crosshair, Layers } from 'lucide-react';
import { useTranslation } from '@/lib/i18n';

// Fix Leaflet default icon issues in Next.js
if (typeof window !== 'undefined') {
  delete (L.Icon.Default.prototype as any)._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  });
}

interface MapLocationPickerProps {
  initialCenter?: { lat: number; lng: number };
  onLocationSelect: (lat: number, lng: number, address?: string) => void;
  height?: string;
  className?: string;
}

interface SearchResult {
  place_id: number;
  display_name: string;
  lat: string;
  lon: string;
}

const EMERGENCY_PRESETS: SearchResult[] = [
  { place_id: 1001, display_name: 'Karachi, Sindh, Pakistan', lat: '24.8607', lon: '67.0011' },
  { place_id: 1002, display_name: 'Lahore, Punjab, Pakistan', lat: '31.5204', lon: '74.3587' },
  { place_id: 1003, display_name: 'Islamabad, Capital Territory, Pakistan', lat: '33.6844', lon: '73.0479' },
  { place_id: 1004, display_name: 'Rawalpindi, Punjab, Pakistan', lat: '33.5651', lon: '73.0169' },
  { place_id: 1005, display_name: 'Peshawar, Khyber Pakhtunkhwa, Pakistan', lat: '34.0151', lon: '71.5249' },
  { place_id: 1006, display_name: 'Quetta, Balochistan, Pakistan', lat: '30.1798', lon: '66.9750' },
  { place_id: 1007, display_name: 'Multan, Punjab, Pakistan', lat: '30.1575', lon: '71.5249' },
  { place_id: 1008, display_name: 'Faisalabad, Punjab, Pakistan', lat: '31.4504', lon: '73.1350' },
  { place_id: 1009, display_name: 'Hyderabad, Sindh, Pakistan', lat: '25.3960', lon: '68.3578' },
  { place_id: 1010, display_name: 'Sukkur, Sindh, Pakistan', lat: '27.7052', lon: '68.8574' },
  { place_id: 1011, display_name: 'Gwadar, Balochistan, Pakistan', lat: '25.1216', lon: '62.3254' },
  { place_id: 1012, display_name: 'Gilgit, Gilgit-Baltistan, Pakistan', lat: '35.9221', lon: '74.3087' },
  { place_id: 1013, display_name: 'Muzaffarabad, Azad Kashmir, Pakistan', lat: '34.3700', lon: '73.4711' },
];

// Custom Neon Cyber Marker Icon
const createCustomIcon = () => {
  if (typeof window === 'undefined') return undefined;
  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `
      <div class="relative flex items-center justify-center w-8 h-8">
        <div class="absolute inset-0 rounded-full bg-pulse-red/40 animate-ping"></div>
        <div class="absolute -inset-1 rounded-full bg-sky-blue/30 blur-sm"></div>
        <div class="relative w-6 h-6 rounded-full bg-gradient-to-tr from-pulse-red to-amber-alert border-2 border-white shadow-lg flex items-center justify-center">
          <div class="w-2 h-2 rounded-full bg-white"></div>
        </div>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

function ChangeMapView({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, 15, { duration: 1.2 });
    map.invalidateSize();
  }, [center, map]);
  return null;
}

function MapResizeHandler() {
  const map = useMap();
  useEffect(() => {
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 200);
    const handleResize = () => {
      map.invalidateSize();
    };
    window.addEventListener('resize', handleResize);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', handleResize);
    };
  }, [map]);
  return null;
}

function MapClickHandler({ onSelect }: { onSelect: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export const MapLocationPicker: React.FC<MapLocationPickerProps> = ({
  initialCenter = { lat: 24.8607, lng: 67.0011 },
  onLocationSelect,
  height = '340px',
  className = '',
}) => {
  const { t } = useTranslation();
  const [mounted, setMounted] = useState(false);
  const [center, setCenter] = useState<[number, number]>([initialCenter.lat, initialCenter.lng]);
  const [markerPos, setMarkerPos] = useState<[number, number]>([initialCenter.lat, initialCenter.lng]);
  const [address, setAddress] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isLocating, setIsLocating] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [mapTheme, setMapTheme] = useState<'dark' | 'standard'>('dark');
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Sync initial center changes if passed
  useEffect(() => {
    if (initialCenter?.lat && initialCenter?.lng) {
      setCenter([initialCenter.lat, initialCenter.lng]);
      setMarkerPos([initialCenter.lat, initialCenter.lng]);
      reverseGeocode(initialCenter.lat, initialCenter.lng);
    }
  }, [initialCenter.lat, initialCenter.lng]);

  // Handle outside clicks to close search suggestions dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);



  // Reverse Geocoding via internal API proxy (safe from CORS, adblockers, and rate limits)
  const reverseGeocode = async (lat: number, lng: number) => {
    try {
      const res = await fetch(`/api/geocode?lat=${lat}&lon=${lng}`);
      if (res.ok) {
        const data = await res.json();
        const formatted = data.display_name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        setAddress(formatted);
        onLocationSelect(lat, lng, formatted);
        return;
      }
    } catch (err) {
      console.warn('Reverse geocode fallback:', err);
    }
    const fallback = `Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)}`;
    setAddress(fallback);
    onLocationSelect(lat, lng, fallback);
  };

  // Search Address / Landmark via internal geocode API
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchQuery.trim();
    if (!query) return;

    setIsSearching(true);
    setShowDropdown(true);

    try {
      const res = await fetch(`/api/geocode?q=${encodeURIComponent(query)}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setSearchResults(data);
          return;
        }
      }
    } catch (err) {
      console.warn('Search geocode fallback:', err);
    } finally {
      setIsSearching(false);
    }

    // Client-side fallback if offline or API returned empty/failed
    const fallbackMatches = EMERGENCY_PRESETS.filter((item) =>
      item.display_name.toLowerCase().includes(query.toLowerCase())
    );
    setSearchResults(fallbackMatches.length > 0 ? fallbackMatches : EMERGENCY_PRESETS.slice(0, 5));
  };

  const selectSearchResult = (result: SearchResult) => {
    const lat = parseFloat(result.lat);
    const lng = parseFloat(result.lon);
    if (!isNaN(lat) && !isNaN(lng)) {
      setCenter([lat, lng]);
      setMarkerPos([lat, lng]);
      setAddress(result.display_name);
      setSearchQuery(result.display_name.split(',')[0]);
      setShowDropdown(false);
      onLocationSelect(lat, lng, result.display_name);
    }
  };

  const handleMapClick = (lat: number, lng: number) => {
    setMarkerPos([lat, lng]);
    setCenter([lat, lng]);
    reverseGeocode(lat, lng);
  };

  // Get User's Current Location via browser Geolocation API
  const handleLocateMe = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser');
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setCenter([lat, lng]);
        setMarkerPos([lat, lng]);
        reverseGeocode(lat, lng);
        setIsLocating(false);
      },
      (err) => {
        console.warn('Geolocation error:', err.message);
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  if (!mounted) {
    return (
      <div
        style={{ height }}
        className="w-full bg-slate-900/80 animate-pulse rounded-2xl border border-white/10 flex flex-col items-center justify-center gap-2 text-slate-400"
      >
        <Loader2 className="animate-spin text-sky-blue" size={28} />
        <span className="text-xs uppercase tracking-widest">Initializing Map...</span>
      </div>
    );
  }

  const customIcon = createCustomIcon();

  return (
    <div className={`relative w-full rounded-2xl overflow-hidden border border-white/15 glass shadow-2xl ${className}`}>
      {/* Top Search Controls Bar */}
      <div className="relative z-[1000] p-3 bg-slate-950/80 backdrop-blur-xl border-b border-white/10" ref={dropdownRef}>
        <form onSubmit={handleSearch} className="flex items-center gap-2">
          <div className="relative flex-grow">
            <input
              id="location-search-input"
              name="location-search"
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                if (!showDropdown && e.target.value.length > 2) {
                  setShowDropdown(true);
                }
              }}
              placeholder={t('search_location_placeholder')}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-9 py-2.5 text-xs sm:text-sm text-warm-white placeholder:text-slate-400 focus:outline-none focus:border-sky-blue focus:ring-1 focus:ring-sky-blue transition-all"
            />
            <Search className="absolute left-3 rtl:right-3 rtl:left-auto top-1/2 -translate-y-1/2 text-sky-blue" size={16} />
            {isSearching && (
              <Loader2 className="absolute right-3 rtl:left-3 rtl:right-auto top-1/2 -translate-y-1/2 animate-spin text-amber-alert" size={16} />
            )}
          </div>

          <button
            type="submit"
            className="px-3 py-2.5 rounded-xl bg-sky-blue/20 hover:bg-sky-blue/30 text-sky-blue border border-sky-blue/30 font-semibold text-xs transition-all flex items-center gap-1 shrink-0 cursor-pointer"
          >
            <Search size={14} />
            <span className="hidden sm:inline">{t('search_btn')}</span>
          </button>

          <button
            type="button"
            onClick={handleLocateMe}
            disabled={isLocating}
            title={t('locate_me')}
            className="p-2.5 rounded-xl bg-pulse-red/20 hover:bg-pulse-red/30 text-pulse-red border border-pulse-red/30 transition-all flex items-center justify-center shrink-0 active:scale-95 cursor-pointer"
          >
            {isLocating ? (
              <Loader2 className="animate-spin" size={18} />
            ) : (
              <Crosshair size={18} className="animate-pulse" />
            )}
          </button>
        </form>

        {/* Search Results Dropdown */}
        {showDropdown && searchResults.length > 0 && (
          <div className="absolute left-3 right-3 top-full mt-2 bg-slate-900/95 border border-white/15 rounded-xl shadow-2xl backdrop-blur-2xl overflow-hidden max-h-60 overflow-y-auto z-[1001]">
            {searchResults.map((item) => (
              <button
                key={item.place_id}
                onClick={() => selectSearchResult(item)}
                className="w-full text-left rtl:text-right px-4 py-3 hover:bg-white/10 border-b border-white/5 last:border-none flex items-start gap-2.5 transition-colors group cursor-pointer"
              >
                <MapPin size={16} className="text-pulse-red shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
                <span className="text-xs text-warm-white line-clamp-2 leading-relaxed">
                  {item.display_name}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Leaflet Interactive Map View */}
      <div style={{ height }} className="w-full relative z-0">
        <MapContainer
          center={center}
          zoom={15}
          style={{ height: '100%', width: '100%' }}
          zoomControl={false}
          className={mapTheme === 'dark' ? 'dark-map' : ''}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={19}
          />
          <MapResizeHandler />
          <ChangeMapView center={center} />
          <MapClickHandler onSelect={handleMapClick} />
          {customIcon && (
            <Marker position={markerPos} icon={customIcon}>
              <Popup className="custom-popup">
                <div className="text-xs p-1 font-sans">
                  <p className="font-bold text-sky-blue mb-1">{t('selected_location')}</p>
                  <p className="text-slate-300">{address || t('detecting_location')}</p>
                </div>
              </Popup>
            </Marker>
          )}
        </MapContainer>

        {/* Floating Controls Overlay */}
        <div className="absolute bottom-3 left-3 right-3 z-[400] flex items-center justify-between gap-2 p-2.5 rounded-xl bg-slate-950/85 backdrop-blur-xl border border-white/10 text-xs">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="p-1.5 rounded-lg bg-relief-green/20 text-relief-green shrink-0">
              <CheckCircle2 size={14} />
            </div>
            <span className="text-slate-300 truncate max-w-[180px] sm:max-w-[280px] font-medium" title={address || t('detecting_location')}>
              {address || t('detecting_location')}
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setMapTheme(prev => prev === 'dark' ? 'standard' : 'dark')}
              className="px-2 py-1 rounded-md bg-white/10 hover:bg-white/20 text-slate-300 hover:text-white border border-white/10 flex items-center gap-1.5 text-[11px] transition-all cursor-pointer"
              title="Toggle Map Style"
            >
              <Layers size={13} className="text-sky-blue" />
              <span className="hidden sm:inline">{mapTheme === 'dark' ? t('tactical_dark') : t('street_map')}</span>
            </button>

            <div className="font-mono tabular-nums text-[10px] text-sky-blue bg-sky-blue/10 px-2 py-1 rounded-md border border-sky-blue/20">
              {markerPos[0].toFixed(4)}, {markerPos[1].toFixed(4)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MapLocationPicker;
