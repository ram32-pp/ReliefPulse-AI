import math
from geopy.geocoders import Nominatim
import asyncio
from typing import Tuple, Optional
from pydantic import BaseModel

# Hardcoded bounding box strictly to Pakistan
PAKISTAN_BOUNDING_BOX = {
    "min_lon": 60.87,
    "min_lat": 23.63,
    "max_lon": 77.83,
    "max_lat": 37.08,
}

class GeocodedLocation(BaseModel):
    coords: Tuple[float, float]  # (latitude, longitude)
    address: str

class GeocodingService:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="reliefpulse_api", timeout=10)
        self.bbox = PAKISTAN_BOUNDING_BOX

    def is_within_pakistan(self, lat: float, lon: float) -> bool:
        """Check if coordinates fall within Pakistan geographic bounding box."""
        return (
            self.bbox["min_lat"] <= lat <= self.bbox["max_lat"]
            and self.bbox["min_lon"] <= lon <= self.bbox["max_lon"]
        )

    def haversine(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """
        Calculate distance between two GPS coordinates in kilometers using Haversine formula.
        """
        R = 6371.0  # Earth radius in km
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2.0) ** 2

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    async def geocode(self, query: str) -> Optional[GeocodedLocation]:
        """
        Geocode location query strictly bounded to Pakistan coordinates.
        """
        try:
            # Nominatim viewbox format: [top-left (lat, lon), bottom-right (lat, lon)]
            viewbox = [
                (self.bbox["max_lat"], self.bbox["min_lon"]),
                (self.bbox["min_lat"], self.bbox["max_lon"]),
            ]
            
            # Run blocking geopy call in a thread with strict Pakistan viewbox and country restriction
            location = await asyncio.to_thread(
                self.geolocator.geocode,
                query,
                viewbox=viewbox,
                bounded=True,
                country_codes=["pk"],
            )

            if location:
                lat, lon = location.latitude, location.longitude
                if self.is_within_pakistan(lat, lon):
                    return GeocodedLocation(
                        coords=(lat, lon),
                        address=location.address
                    )
            return None
        except Exception as e:
            print(f"Geocoding error for '{query}': {e}")
            return None

geocoding_service = GeocodingService()
