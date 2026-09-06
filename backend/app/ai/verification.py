from typing import Dict, Any, Tuple, Optional

class LocationValidation:
    def __init__(
        self,
        match_level: str,
        confidence: float,
        flag: Optional[str] = None,
        distance_km: float = 0.0,
        spatial_mismatch: bool = False,
        geocoded_coords: Optional[Tuple[float, float]] = None,
    ):
        self.match_level = match_level
        self.confidence = confidence
        self.flag = flag
        self.distance_km = distance_km
        self.spatial_mismatch = spatial_mismatch
        self.geocoded_coords = geocoded_coords


async def cross_reference_location(
    gps_coords: Tuple[float, float],
    extracted_location: str,
    extracted_city: Optional[str] = None,
) -> LocationValidation:
    """
    Cross-reference device GPS coordinates against extracted text landmark using
    strict Pakistan bounding box geocoding and Haversine distance calculation.
    Flags spatial_mismatch = True if discrepancy exceeds 5km.
    """
    from app.services.geocoding_service import geocoding_service

    query = f"{extracted_location}, {extracted_city or 'Pakistan'}"
    geocoded = await geocoding_service.geocode(query)

    if not geocoded:
        return LocationValidation(
            match_level="unverifiable",
            confidence=0.0,
            flag="Could not geocode extracted landmark within Pakistan bounds",
            distance_km=0.0,
            spatial_mismatch=False,
        )

    distance_km = geocoding_service.haversine(gps_coords, geocoded.coords)
    is_mismatch = distance_km > 5.0

    if distance_km < 1.0:
        return LocationValidation(
            match_level="exact",
            confidence=0.95,
            distance_km=distance_km,
            spatial_mismatch=False,
            geocoded_coords=geocoded.coords,
        )
    elif distance_km <= 5.0:
        return LocationValidation(
            match_level="neighborhood",
            confidence=0.80,
            distance_km=distance_km,
            spatial_mismatch=False,
            geocoded_coords=geocoded.coords,
        )
    elif distance_km < 20.0:
        return LocationValidation(
            match_level="city",
            confidence=0.40,
            flag=f"GPS is {distance_km:.1f}km from reported landmark (exceeds 5km threshold)",
            distance_km=distance_km,
            spatial_mismatch=True,
            geocoded_coords=geocoded.coords,
        )
    else:
        return LocationValidation(
            match_level="mismatch",
            confidence=0.10,
            flag=f"Severe spatial discrepancy: GPS is {distance_km:.1f}km from reported landmark",
            distance_km=distance_km,
            spatial_mismatch=True,
            geocoded_coords=geocoded.coords,
        )


async def pre_verify(extraction: Dict[str, Any], gps_coords: Optional[Tuple[float, float]] = None) -> Dict[str, Any]:
    """
    Pre-verification engine: validates landmark distance, detects spatial mismatch,
    and routes discrepancies >5km to coordinator for manual review.
    """
    verification = {
        "is_verified": False,
        "adjusted_confidence": extraction.get("confidence_score", 0.0),
        "gps_match": None,
        "spatial_mismatch": False,
        "distance_km": 0.0,
        "anomalies": list(extraction.get("anomaly_flags", [])),
    }

    # Fail-open: Never auto-reject reports. Low confidence flags for coordinator review.
    if verification["adjusted_confidence"] < 0.3:
        verification["is_verified"] = False
        verification["action"] = "manual_review"
        return verification

    if gps_coords and extraction.get("location"):
        loc = extraction["location"]
        extracted_name = loc.get("extracted_name", "") or loc.get("landmark", "")
        city = loc.get("city")

        if extracted_name:
            match = await cross_reference_location(gps_coords, extracted_name, city)
            verification["gps_match"] = {
                "level": match.match_level,
                "confidence": match.confidence,
                "distance_km": match.distance_km,
                "spatial_mismatch": match.spatial_mismatch,
            }
            verification["distance_km"] = match.distance_km
            verification["spatial_mismatch"] = match.spatial_mismatch

            if match.spatial_mismatch or match.distance_km > 5.0:
                verification["spatial_mismatch"] = True
                verification["action"] = "manual_review"
                verification["anomalies"].append({
                    "flag_type": "spatial_mismatch",
                    "description": f"Spatial mismatch: Device GPS is {match.distance_km:.1f}km from claimed landmark '{extracted_name}' (exceeds 5km threshold). Routed to coordinator for manual review.",
                    "severity": "critical",
                })
            elif match.flag:
                verification["anomalies"].append({
                    "flag_type": "vague_location",
                    "description": match.flag,
                    "severity": "warning",
                })

    critical_anomalies = [
        a for a in verification["anomalies"]
        if isinstance(a, dict) and a.get("severity") == "critical"
    ]

    if critical_anomalies or verification.get("spatial_mismatch"):
        verification["action"] = "manual_review"
        verification["is_verified"] = False
    else:
        verification["is_verified"] = True
        verification["action"] = "route_to_clustering"

    return verification
