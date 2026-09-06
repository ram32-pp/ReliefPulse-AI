'use client';

import React from 'react';
import dynamic from 'next/dynamic';

const MapLocationPicker = dynamic(
  () => import('./MapLocationPicker').then((mod) => mod.MapLocationPicker),
  {
    ssr: false,
    loading: () => (
      <div className="h-[340px] w-full bg-slate-900/80 animate-pulse rounded-2xl border border-white/10 flex items-center justify-center text-slate-400 text-xs">
        Loading Interactive Map...
      </div>
    ),
  }
);

interface LocationPickerProps {
  initialCenter: [number, number] | { lat: number; lng: number };
  onLocationSelect: (lat: number, lng: number, address?: string) => void;
  height?: string;
}

export const LocationPicker: React.FC<LocationPickerProps> = ({ initialCenter, onLocationSelect, height }) => {
  const centerObj = Array.isArray(initialCenter)
    ? { lat: initialCenter[0], lng: initialCenter[1] }
    : initialCenter;

  return (
    <MapLocationPicker
      initialCenter={centerObj}
      onLocationSelect={onLocationSelect}
      height={height || '340px'}
    />
  );
};

export default LocationPicker;

