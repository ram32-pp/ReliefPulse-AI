'use client';

import { useState, useEffect, useCallback } from 'react';

export interface Coordinates {
  latitude: number;
  longitude: number;
  accuracy: number;
}

export interface GeolocationState {
  coords: Coordinates | null;
  error: string | null;
  loading: boolean;
}

export const useGeolocation = () => {
  const [state, setState] = useState<GeolocationState>({
    coords: null,
    error: null,
    loading: true,
  });

  // Watch position on mount for live telemetry
  useEffect(() => {
    if (typeof window === 'undefined' || !('geolocation' in navigator)) {
      setState({ coords: null, error: 'Geolocation not supported by device', loading: false });
      return;
    }

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        setState({
          coords: {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          },
          error: null,
          loading: false,
        });
      },
      (error) => {
        setState((prev) => ({ ...prev, error: error.message, loading: false }));
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, []);

  /**
   * Imperatively request high-accuracy GPS fix upon form submission or user trigger.
   * Enforces enableHighAccuracy: true, maximumAge: 0, timeout: 10000.
   */
  const getCurrentLocation = useCallback(async (): Promise<Coordinates> => {
    return new Promise((resolve, reject) => {
      if (typeof window === 'undefined' || !('geolocation' in navigator)) {
        const err = new Error('Geolocation is not supported by your browser or device');
        setState((prev) => ({ ...prev, error: err.message }));
        return reject(err);
      }

      setState((prev) => ({ ...prev, loading: true }));

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const freshCoords: Coordinates = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          };
          setState({
            coords: freshCoords,
            error: null,
            loading: false,
          });
          resolve(freshCoords);
        },
        (error) => {
          setState((prev) => ({ ...prev, error: error.message, loading: false }));
          reject(new Error(`GPS Acquisition Failed: ${error.message}`));
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0,
        }
      );
    });
  }, []);

  return {
    ...state,
    getCurrentLocation,
  };
};
