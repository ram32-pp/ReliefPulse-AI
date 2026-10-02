'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { ClusterMarker } from './ClusterMarker';

interface LiveMapProps {
  selectedIncident: string | null;
  onMarkerClick: (id: string) => void;
  incidents?: any[];
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

function FocusIncident({
  clusters,
  selectedId,
}: {
  clusters: { id: string; lat: number; lng: number }[];
  selectedId: string | null;
}) {
  const map = useMap();
  useEffect(() => {
    if (selectedId) {
      const found = clusters.find(
        (c) =>
          c.id.toLowerCase() === selectedId.toLowerCase() ||
          c.id.toLowerCase().includes(selectedId.toLowerCase()) ||
          selectedId.toLowerCase().includes(c.id.toLowerCase())
      );
      if (found && !isNaN(found.lat) && !isNaN(found.lng)) {
        map.flyTo([found.lat, found.lng], 14, { duration: 1 });
      }
    }
  }, [selectedId, clusters, map]);
  return null;
}

export default function LiveMap({ selectedIncident, onMarkerClick, incidents }: LiveMapProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const clusters = useMemo(() => {
    if (incidents && incidents.length > 0) {
      return incidents.map((inc, index) => {
        const id = inc.incident_id || inc.incident_code || inc.id || `inc-${index}`;
        const rawLat =
          inc.location?.centroid?.lat ??
          inc.location?.lat ??
          inc.latitude ??
          (24.8607 + (index * 0.02 - 0.03));
        const rawLng =
          inc.location?.centroid?.lng ??
          inc.location?.lng ??
          inc.longitude ??
          (67.0011 + (index * 0.02 - 0.03));
        const count = inc.total_reports || inc.reports_count || 1;
        const severity = (inc.severity || 'high') as 'critical' | 'high' | 'medium' | 'low';
        return {
          id: String(id),
          lat: Number(rawLat),
          lng: Number(rawLng),
          count: Number(count),
          severity,
        };
      });
    }
    return [];
  }, [incidents]);

  if (!mounted) {
    return (
      <div className="h-full w-full bg-slate-950 flex flex-col items-center justify-center text-slate-400 text-xs">
        <div className="w-6 h-6 rounded-full border-2 border-sky-blue border-t-transparent animate-spin mb-2" />
        <span>Loading Command Center Map...</span>
      </div>
    );
  }

  const defaultCenter: [number, number] =
    clusters.length > 0 && !isNaN(clusters[0].lat) && !isNaN(clusters[0].lng)
      ? [clusters[0].lat, clusters[0].lng]
      : [24.8607, 67.0011];

  return (
    <div className="h-full w-full z-0">
      <MapContainer
        center={defaultCenter}
        zoom={12}
        style={{ height: '100%', width: '100%' }}
        className="dark-map"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <MapResizeHandler />
        <FocusIncident clusters={clusters} selectedId={selectedIncident} />
        {clusters.map((cluster) => (
          <ClusterMarker
            key={cluster.id}
            {...cluster}
            isSelected={
              selectedIncident !== null &&
              (selectedIncident.toLowerCase() === cluster.id.toLowerCase() ||
                cluster.id.toLowerCase().includes(selectedIncident.toLowerCase()))
            }
            onClick={() => onMarkerClick(cluster.id)}
          />
        ))}
      </MapContainer>
    </div>
  );
}
