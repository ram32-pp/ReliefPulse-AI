'use client';

import React from 'react';
import { Marker } from 'react-leaflet';
import L from 'leaflet';

interface ClusterMarkerProps {
  id: string;
  lat: number;
  lng: number;
  count: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  isSelected: boolean;
  onClick: () => void;
}

export const ClusterMarker: React.FC<ClusterMarkerProps> = ({ id, lat, lng, count, severity, isSelected, onClick }) => {
  const bgColors = {
    critical: '#E63946',
    high: '#F4A261',
    medium: '#4EA8DE',
    low: '#6B7280',
  };
  
  const bgColor = bgColors[severity];
  const pulseClass = severity === 'critical' ? 'animate-pulse' : '';
  const ringClass = isSelected ? 'ring-4 ring-white shadow-xl' : 'shadow-md';
  const size = Math.min(60, Math.max(32, 32 + (count * 2)));

  const iconMarkup = `
    <div 
      style="background-color: ${bgColor}; width: ${size}px; height: ${size}px;" 
      class="rounded-full text-white flex items-center justify-center font-bold text-sm border-2 border-white ${ringClass} ${pulseClass}"
    >
      ${count}
    </div>
  `;

  const customIcon = L.divIcon({
    html: iconMarkup,
    className: 'custom-cluster-icon',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });

  return (
    <Marker 
      position={[lat, lng]} 
      icon={customIcon}
      eventHandlers={{ click: onClick }}
    />
  );
};
