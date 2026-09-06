'use client';

import React, { useState, useCallback } from 'react';
import { GoogleMap, useJsApiLoader, Marker } from '@react-google-maps/api';

interface LocationPickerProps {
  initialCenter: { lat: number; lng: number };
  onLocationSelect: (lat: number, lng: number) => void;
}

const containerStyle = {
  width: '100%',
  height: '100%'
};

export const GoogleLocationPicker: React.FC<LocationPickerProps> = ({ initialCenter, onLocationSelect }) => {
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || ''
  });

  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [markerPosition, setMarkerPosition] = useState(initialCenter);

  const onLoad = useCallback(function callback(map: google.maps.Map) {
    setMap(map);
  }, []);

  const onUnmount = useCallback(function callback(map: google.maps.Map) {
    setMap(null);
  }, []);

  const handleMapClick = (e: google.maps.MapMouseEvent) => {
    if (e.latLng) {
      const lat = e.latLng.lat();
      const lng = e.latLng.lng();
      setMarkerPosition({ lat, lng });
      onLocationSelect(lat, lng);
    }
  };

  if (!isLoaded) {
    return <div className="h-[300px] w-full bg-slate-200 animate-pulse rounded-lg flex items-center justify-center text-slate-500">Loading Map...</div>;
  }

  return (
    <div className="h-[300px] w-full rounded-lg overflow-hidden border border-slate-300">
      <GoogleMap
        mapContainerStyle={containerStyle}
        center={initialCenter}
        zoom={15}
        onLoad={onLoad}
        onUnmount={onUnmount}
        onClick={handleMapClick}
        options={{
          disableDefaultUI: true,
          zoomControl: true,
        }}
      >
        <Marker position={markerPosition} />
      </GoogleMap>
    </div>
  );
};

export default GoogleLocationPicker;
