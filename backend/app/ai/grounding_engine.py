"""
Asymmetric Grounding Engine — Resolves the "Google Search Grounding Freshness Paradox".

Core principle: Disasters break infrastructure before journalists publish articles.
Therefore, ABSENCE of grounding data must NEVER penalize a report.

Scoring model:
  - Match found from authoritative source → boost +20 to +30
  - No match found from any source        → boost +0 (neutral, NOT negative)

Queries three sources in parallel:
  1. USGS Earthquake Feed (public, no API key)
  2. OpenWeatherMap Alert API (optional API key)
  3. Google Search Grounding via Gemini (existing)
"""

import asyncio
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel, Field

from app.config import settings


class GroundingSource(BaseModel):
    """A single authoritative grounding source result."""
    source_name: str
    source_type: str  # "earthquake_feed" | "weather_alert" | "web_search"
    matched: bool
    summary: str
    citations: List[Dict[str, str]] = Field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None


class GroundingResult(BaseModel):
    """Aggregated result from the Asymmetric Grounding Engine."""
    grounding_boost: int = 0  # Points to add to rubric score (0 to +30, never negative)
    grounding_label: str = "neutral"  # "authority_confirmed" | "unreported_localized_incident" | "neutral"
    sources_queried: int = 0
    sources_matched: int = 0
    source_results: List[GroundingSource] = Field(default_factory=list)
    combined_summary: str = ""


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in km."""
    R = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class AsymmetricGroundingEngine:
    """
    Queries multiple authoritative disaster sources in parallel and applies
    asymmetric scoring: evidence of disaster boosts the score, but absence
    of evidence never penalizes it.
    """

    def __init__(self):
        self.owm_api_key = settings.openweathermap_api_key.strip()
        self.gemini_api_key = settings.gemini_api_key.strip()

    async def run_grounding(
        self,
        location_name: str,
        gps_coords: Optional[Tuple[float, float]] = None,
        hazard_context: str = "",
    ) -> GroundingResult:
        """
        Query all grounding sources in parallel and aggregate results.
        """
        tasks = []

        # Always try USGS (no key needed) with hazard relevance check
        tasks.append(self._query_usgs_earthquake(gps_coords, hazard_context))

        # OpenWeatherMap if key available
        if self.owm_api_key:
            tasks.append(self._query_openweathermap_alerts(gps_coords, hazard_context))
        else:
            tasks.append(self._no_op_source("OpenWeatherMap", "weather_alert", "API key not configured"))

        # Google Search Grounding via Gemini
        tasks.append(self._query_gemini_search_grounding(location_name, hazard_context))

        # Run all in parallel with individual timeout protection
        results = await asyncio.gather(*tasks, return_exceptions=True)

        source_results: List[GroundingSource] = []
        for r in results:
            if isinstance(r, GroundingSource):
                source_results.append(r)
            elif isinstance(r, Exception):
                print(f"[GroundingEngine] Source query exception: {r}")
                source_results.append(GroundingSource(
                    source_name="Unknown",
                    source_type="error",
                    matched=False,
                    summary=f"Query failed: {str(r)[:100]}",
                ))

        sources_queried = len(source_results)
        sources_matched = sum(1 for s in source_results if s.matched)

        # Asymmetric scoring: presence boosts, absence is neutral
        if sources_matched >= 2:
            grounding_boost = 30
            grounding_label = "authority_confirmed"
        elif sources_matched == 1:
            grounding_boost = 20
            grounding_label = "authority_confirmed"
        else:
            # Zero penalty — this is the critical asymmetric design
            grounding_boost = 0
            grounding_label = "unreported_localized_incident"

        summaries = [s.summary for s in source_results if s.summary]
        combined_summary = " | ".join(summaries[:3]) if summaries else "No authoritative matches found; treating as unreported localized incident (no penalty applied)."

        return GroundingResult(
            grounding_boost=grounding_boost,
            grounding_label=grounding_label,
            sources_queried=sources_queried,
            sources_matched=sources_matched,
            source_results=source_results,
            combined_summary=combined_summary,
        )

    async def _query_usgs_earthquake(
        self, gps_coords: Optional[Tuple[float, float]], hazard_context: str = ""
    ) -> GroundingSource:
        """Query USGS Earthquake Hazards Program feed for recent seismic activity relevant to claim."""
        source = GroundingSource(
            source_name="USGS Earthquake Hazards Program",
            source_type="earthquake_feed",
            matched=False,
            summary="No recent seismic activity detected near location.",
        )

        # Invariant: Only corroborate if report claims seismic/earthquake/structural collapse
        hazard_lower = (hazard_context or "").lower()
        seismic_keywords = [
            "earthquake", "zalzala", "tremor", "seismic", "aftershock",
            "shaking", "hil raha", "jhatkay", "collapse", "imarat", "debris"
        ]
        is_seismic_claim = any(k in hazard_lower for k in seismic_keywords)

        if hazard_context and not is_seismic_claim:
            source.summary = "Seismic feed not applicable to non-seismic emergency report."
            return source

        if not gps_coords:
            source.summary = "No GPS coordinates provided for earthquake check."
            return source

        lat, lng = gps_coords

        try:
            # Query recent earthquakes in the last 7 days (freshness invariant for emergency dispatch)
            url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            features = data.get("features", [])
            nearby = []
            now_ms = time.time() * 1000.0
            max_age_ms = 48 * 3600 * 1000.0  # Last 48 hours for active emergency relevance

            for feature in features:
                coords = feature.get("geometry", {}).get("coordinates", [])
                props = feature.get("properties", {})
                eq_time = props.get("time", 0)

                # Freshness check: must be within the last 48 hours
                if eq_time and (now_ms - eq_time > max_age_ms):
                    continue

                if len(coords) >= 2:
                    eq_lng, eq_lat = coords[0], coords[1]
                    dist = _haversine_km(lat, lng, eq_lat, eq_lng)
                    if dist <= 150:  # Within 150km of epicentre
                        nearby.append({
                            "magnitude": props.get("mag"),
                            "place": props.get("place"),
                            "time": props.get("time"),
                            "distance_km": round(dist, 1),
                            "url": props.get("url"),
                        })

            if nearby:
                nearby.sort(key=lambda x: x["distance_km"])
                closest = nearby[0]
                source.matched = True
                source.summary = (
                    f"Active seismic activity confirmed: M{closest['magnitude']} earthquake "
                    f"at {closest['place']}, {closest['distance_km']}km away in past 48h. "
                    f"{len(nearby)} recent events within 150km."
                )
                source.citations = [
                    {"title": f"M{n['magnitude']} - {n['place']}", "url": n.get("url", "")}
                    for n in nearby[:3]
                ]
                source.raw_data = {"nearby_events": nearby[:5]}
            else:
                source.summary = "No seismic events >= M2.5 within 150km in the past 48 hours."

        except Exception as e:
            source.summary = f"USGS query failed ({str(e)[:80]}); no penalty applied."

        return source

    async def _query_openweathermap_alerts(
        self, gps_coords: Optional[Tuple[float, float]], hazard_context: str = ""
    ) -> GroundingSource:
        """Query OpenWeatherMap One Call API for active weather alerts relevant to claim."""
        source = GroundingSource(
            source_name="OpenWeatherMap Alerts",
            source_type="weather_alert",
            matched=False,
            summary="No active weather alerts for location.",
        )

        if not gps_coords:
            source.summary = "No GPS coordinates provided for weather alert check."
            return source

        lat, lng = gps_coords

        try:
            url = (
                f"https://api.openweathermap.org/data/3.0/onecall"
                f"?lat={lat}&lon={lng}&exclude=minutely,hourly,daily"
                f"&appid={self.owm_api_key}"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

            alerts = data.get("alerts", [])
            if alerts:
                alert_summaries = []
                for alert in alerts[:3]:
                    event = alert.get("event", "Weather Alert")
                    sender = alert.get("sender_name", "Weather Authority")
                    desc = alert.get("description", "")[:150]
                    alert_summaries.append(f"{event} ({sender}): {desc}")

                source.matched = True
                source.summary = f"{len(alerts)} active weather alert(s): " + "; ".join(alert_summaries)
                source.citations = [
                    {"title": a.get("event", "Alert"), "url": ""}
                    for a in alerts[:3]
                ]
                source.raw_data = {"alerts": alerts[:5]}

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                source.summary = "OpenWeatherMap API key invalid; no penalty applied."
            else:
                source.summary = f"OpenWeatherMap query failed ({e.response.status_code}); no penalty applied."
        except Exception as e:
            source.summary = f"OpenWeatherMap query failed ({str(e)[:80]}); no penalty applied."

        return source

    async def _query_gemini_search_grounding(
        self, location_name: str, hazard_context: str
    ) -> GroundingSource:
        """Use Gemini with Google Search Grounding for real-time news/alert checking."""
        source = GroundingSource(
            source_name="Google Search Grounding (Gemini)",
            source_type="web_search",
            matched=False,
            summary="No disaster-related search results matched.",
        )

        if not self.gemini_api_key or self.gemini_api_key == "your_gemini_api_key":
            source.summary = "Gemini API key not configured; no penalty applied."
            return source

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.gemini_api_key)

            search_prompt = (
                f"Check real-time emergency reports, disaster alerts, and weather bulletins "
                f"for location: '{location_name}'. Context: '{hazard_context[:200]}'. "
                f"Is there an active disaster, severe weather, or emergency in this area? "
                f"Answer briefly and cite sources."
            )

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.gemini_model or "gemini-2.5-flash",
                contents=search_prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.2,
                ),
            )

            text = response.text or ""
            citations = []

            if response.candidates and response.candidates[0].grounding_metadata:
                gm = response.candidates[0].grounding_metadata
                if hasattr(gm, "grounding_chunks") and gm.grounding_chunks:
                    for chunk in gm.grounding_chunks:
                        if hasattr(chunk, "web") and chunk.web:
                            citations.append({
                                "title": getattr(chunk.web, "title", "Web Source"),
                                "url": getattr(chunk.web, "uri", ""),
                            })

            disaster_keywords = [
                "flood", "rain", "warning", "alert", "emergency", "disaster",
                "inundated", "casualties", "evacuation", "earthquake", "fire",
                "storm", "cyclone", "landslide", "rescue",
            ]
            matched = any(w in text.lower() for w in disaster_keywords)

            if matched:
                source.matched = True
                source.summary = text[:300] + ("..." if len(text) > 300 else "")
                source.citations = citations[:4]

        except Exception as e:
            source.summary = f"Gemini grounding query failed ({str(e)[:80]}); no penalty applied."

        return source

    async def _no_op_source(self, name: str, source_type: str, reason: str) -> GroundingSource:
        """Return a non-matched source placeholder when a source is unavailable."""
        return GroundingSource(
            source_name=name,
            source_type=source_type,
            matched=False,
            summary=f"{name} not queried: {reason}. No penalty applied.",
        )


# Module-level singleton
grounding_engine = AsymmetricGroundingEngine()
