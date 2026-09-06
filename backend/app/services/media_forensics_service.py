"""
Media Forensics Service — EXIF validation, perceptual hash deduplication,
and media source classification for anti-spoofing.

Three core responsibilities:
1. EXIF GPS/timestamp extraction and Haversine spoof detection
2. Perceptual hash (pHash) computation and duplicate detection
3. Media source classification (live_camera vs gallery_unverified)
"""

import io
import math
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any

from app.config import settings

# Attempt to import image processing libraries — degrade gracefully if not installed
try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

try:
    import piexif
    _PIEXIF_AVAILABLE = True
except ImportError:
    _PIEXIF_AVAILABLE = False

try:
    import imagehash
    _IMAGEHASH_AVAILABLE = True
except ImportError:
    _IMAGEHASH_AVAILABLE = False


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance in kilometers between two GPS points."""
    R = 6371.0  # Earth radius in km
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _dms_to_decimal(dms_tuple: tuple, ref: str) -> float:
    """Convert EXIF DMS (degrees, minutes, seconds) to decimal degrees."""
    try:
        degrees = dms_tuple[0][0] / dms_tuple[0][1]
        minutes = dms_tuple[1][0] / dms_tuple[1][1]
        seconds = dms_tuple[2][0] / dms_tuple[2][1]
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except (IndexError, ZeroDivisionError, TypeError):
        return 0.0


class MediaForensicsService:
    """
    Provides EXIF sanity validation, perceptual hash computation,
    and media provenance classification for emergency SOS reports.
    """

    def __init__(self):
        self.phash_hamming_threshold = settings.phash_hamming_threshold

    def extract_exif_metadata(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extract GPS coordinates and timestamp from image EXIF data.

        Returns dict with:
            - exif_lat, exif_lng: GPS coordinates (or None)
            - exif_timestamp: datetime (or None)
            - has_gps: bool
            - has_timestamp: bool
        """
        result: Dict[str, Any] = {
            "exif_lat": None,
            "exif_lng": None,
            "exif_timestamp": None,
            "has_gps": False,
            "has_timestamp": False,
        }

        if not _PIEXIF_AVAILABLE or not image_bytes:
            return result

        try:
            exif_dict = piexif.load(image_bytes)
        except Exception:
            return result

        # Extract GPS
        gps_data = exif_dict.get("GPS", {})
        if gps_data:
            lat_dms = gps_data.get(piexif.GPSIFD.GPSLatitude)
            lat_ref = gps_data.get(piexif.GPSIFD.GPSLatitudeRef, b"N")
            lng_dms = gps_data.get(piexif.GPSIFD.GPSLongitude)
            lng_ref = gps_data.get(piexif.GPSIFD.GPSLongitudeRef, b"E")

            if lat_dms and lng_dms:
                if isinstance(lat_ref, bytes):
                    lat_ref = lat_ref.decode("ascii", errors="ignore")
                if isinstance(lng_ref, bytes):
                    lng_ref = lng_ref.decode("ascii", errors="ignore")

                result["exif_lat"] = _dms_to_decimal(lat_dms, lat_ref)
                result["exif_lng"] = _dms_to_decimal(lng_dms, lng_ref)
                result["has_gps"] = True

        # Extract timestamp
        exif_ifd = exif_dict.get("Exif", {})
        datetime_original = exif_ifd.get(piexif.ExifIFD.DateTimeOriginal)
        if not datetime_original:
            ifd0 = exif_dict.get("0th", {})
            datetime_original = ifd0.get(piexif.ImageIFD.DateTime)

        if datetime_original:
            if isinstance(datetime_original, bytes):
                datetime_original = datetime_original.decode("ascii", errors="ignore")
            try:
                result["exif_timestamp"] = datetime.strptime(
                    datetime_original, "%Y:%m:%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
                result["has_timestamp"] = True
            except (ValueError, TypeError):
                pass

        return result

    def validate_exif_against_device(
        self,
        image_bytes: bytes,
        device_lat: Optional[float],
        device_lng: Optional[float],
    ) -> Dict[str, Any]:
        """
        Cross-reference EXIF data against device-reported GPS.

        Returns dict with:
            - flag_location_spoof: bool (True if delta > 2km or timestamp > 30min old)
            - exif_metadata: dict of extracted EXIF data
            - distance_km: float or None
            - timestamp_age_minutes: float or None
            - spoof_reasons: list of strings
        """
        exif_data = self.extract_exif_metadata(image_bytes)
        spoof_reasons: list[str] = []
        flag_spoof = False
        distance_km: Optional[float] = None
        timestamp_age_minutes: Optional[float] = None

        # GPS distance check
        if exif_data["has_gps"] and device_lat is not None and device_lng is not None:
            distance_km = _haversine(
                device_lat, device_lng,
                exif_data["exif_lat"], exif_data["exif_lng"],
            )
            if distance_km > 2.0:
                flag_spoof = True
                spoof_reasons.append(
                    f"EXIF GPS is {distance_km:.1f}km from device GPS (threshold: 2.0km)"
                )

        # Timestamp freshness check
        if exif_data["has_timestamp"] and exif_data["exif_timestamp"]:
            now = datetime.now(timezone.utc)
            age = now - exif_data["exif_timestamp"]
            timestamp_age_minutes = age.total_seconds() / 60.0
            if timestamp_age_minutes > 30:
                flag_spoof = True
                spoof_reasons.append(
                    f"EXIF timestamp is {timestamp_age_minutes:.0f} minutes old (threshold: 30min)"
                )

        return {
            "flag_location_spoof": flag_spoof,
            "exif_metadata": exif_data,
            "distance_km": distance_km,
            "timestamp_age_minutes": timestamp_age_minutes,
            "spoof_reasons": spoof_reasons,
        }

    def compute_phash(self, image_bytes: bytes) -> Optional[str]:
        """
        Compute a 64-bit perceptual hash for an image.

        Returns hex string of the pHash, or None if computation fails.
        """
        if not _PIL_AVAILABLE or not _IMAGEHASH_AVAILABLE or not image_bytes:
            return None

        try:
            img = Image.open(io.BytesIO(image_bytes))
            h = imagehash.phash(img)
            return str(h)
        except Exception as e:
            print(f"[MediaForensics] pHash computation failed: {e}")
            return None

    def compute_video_keyframe_phash(self, video_bytes: bytes) -> Optional[str]:
        """
        Extract a keyframe from video and compute its pHash.

        Uses the first frame as a basic keyframe. For production,
        consider using ffmpeg to extract multiple keyframes.
        """
        if not _PIL_AVAILABLE or not _IMAGEHASH_AVAILABLE or not video_bytes:
            return None

        try:
            # Attempt to extract first frame using PIL (works for some formats)
            img = Image.open(io.BytesIO(video_bytes))
            img = img.convert("RGB")
            h = imagehash.phash(img)
            return str(h)
        except Exception:
            # Video frame extraction failed — not critical for verification
            return None

    def check_phash_duplicate(
        self, phash_hex: str, existing_hashes: list[str]
    ) -> Dict[str, Any]:
        """
        Check if a pHash is a near-duplicate of any existing hash using Hamming distance.

        Args:
            phash_hex: hex string of the new image's pHash
            existing_hashes: list of hex strings from existing reports

        Returns:
            dict with 'is_duplicate', 'closest_distance', 'closest_hash'
        """
        if not _IMAGEHASH_AVAILABLE or not phash_hex:
            return {"is_duplicate": False, "closest_distance": None, "closest_hash": None}

        try:
            new_hash = imagehash.hex_to_hash(phash_hex)
        except Exception:
            return {"is_duplicate": False, "closest_distance": None, "closest_hash": None}

        closest_distance = float("inf")
        closest_hash = None

        for existing_hex in existing_hashes:
            if not existing_hex:
                continue
            try:
                existing_hash = imagehash.hex_to_hash(existing_hex)
                distance = new_hash - existing_hash  # Hamming distance
                if distance < closest_distance:
                    closest_distance = distance
                    closest_hash = existing_hex
            except Exception:
                continue

        is_duplicate = bool(closest_distance <= self.phash_hamming_threshold)

        return {
            "is_duplicate": is_duplicate,
            "closest_distance": int(closest_distance) if closest_distance != float("inf") else None,
            "closest_hash": closest_hash if is_duplicate else None,
        }


    def classify_media_source(
        self,
        declared_source: Optional[str] = None,
        nonce_validated: bool = False,
        has_media: bool = True,
    ) -> str:
        """
        Classify media source based on client claim, media presence, and nonce verification.

        - If no media was submitted -> 'no_media'
        - If declared as 'gallery_unverified' -> 'gallery_unverified'
        - If declared as 'live_camera' and nonce is validated -> 'live_camera'
        - If declared as 'live_camera' but nonce is invalid/missing -> 'gallery_unverified'
        - If undeclared -> 'live_camera' if nonce_validated else ('gallery_unverified' if has_media else 'no_media')
        """
        if not has_media or declared_source in ("no_media", "none"):
            return "no_media"
        if declared_source == "gallery_unverified":
            return "gallery_unverified"
        if nonce_validated:
            return "live_camera"
        return "gallery_unverified"

    async def run_full_forensics(
        self,
        image_bytes: Optional[bytes] = None,
        video_bytes: Optional[bytes] = None,
        device_lat: Optional[float] = None,
        device_lng: Optional[float] = None,
        existing_phashes: Optional[list[str]] = None,
        nonce_validated: bool = False,
        has_media: Optional[bool] = None,
    ) -> Dict[str, Any]:

        """
        Run the complete media forensics pipeline.

        Returns a consolidated forensics result dict.
        """
        if has_media is None:
            has_media = bool(image_bytes or video_bytes)
        media_source = self.classify_media_source(
            declared_source="live_camera" if nonce_validated else None,
            nonce_validated=nonce_validated,
            has_media=has_media,
        )

        result: Dict[str, Any] = {
            "media_source": media_source,
            "has_media": has_media,
            "flag_location_spoof": False,
            "exif_metadata": None,
            "phash": None,
            "phash_duplicate": {"is_duplicate": False, "closest_distance": None, "closest_hash": None},
            "spoof_reasons": [],
        }

        media_bytes = image_bytes or video_bytes

        # EXIF validation (only for images with EXIF support)
        if image_bytes:
            exif_result = self.validate_exif_against_device(
                image_bytes, device_lat, device_lng
            )
            result["flag_location_spoof"] = exif_result["flag_location_spoof"]
            result["exif_metadata"] = exif_result["exif_metadata"]
            result["spoof_reasons"] = exif_result["spoof_reasons"]

        # pHash computation
        if image_bytes:
            result["phash"] = self.compute_phash(image_bytes)
        elif video_bytes:
            result["phash"] = self.compute_video_keyframe_phash(video_bytes)

        # Duplicate check
        if result["phash"] and existing_phashes:
            result["phash_duplicate"] = self.check_phash_duplicate(
                result["phash"], existing_phashes
            )

        return result


# Module-level singleton
media_forensics_service = MediaForensicsService()
