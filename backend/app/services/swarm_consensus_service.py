"""
Layer 2: Spatiotemporal Multi-Witness Consensus Engine (The "Swarm Effect").

Responsibilities:
1. Query independent emergency distress reports within a 500-meter radius over a 15-minute window.
2. Group by distinct physical device IDs and client fingerprints (Sybil-resistant).
3. Compute the Cluster Density Factor:
   C_d = ln(1 + N_unique_devices)
4. Inject C_d as a multiplier / bonus into verification score.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession


def _haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate Great-Circle distance in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class SwarmConsensusResult(BaseModel):
    cluster_density_factor: float = 0.0  # C_d = ln(1 + N_unique_devices)
    unique_devices_count: int = 1
    total_corroborating_reports: int = 1
    swarm_consensus_achieved: bool = False  # True if >= 2 distinct devices in 500m/15min
    cluster_bonus_pts: int = 0  # 0 to 25 bonus points
    cluster_score: float = 0.25  # 0.0 to 1.0 normalized score
    flags: List[str] = Field(default_factory=list)


class SwarmConsensusService:
    """
    Evaluates independent co-location reports to achieve mathematical swarm consensus.
    """

    def compute_cluster_density(self, unique_devices_count: int) -> float:
        """
        Calculate C_d = ln(1 + N_unique_devices).
        """
        n = max(0, unique_devices_count)
        return round(math.log(1.0 + n), 4)

    def calculate_swarm_bonus(self, cd: float, unique_devices: int) -> int:
        """
        Calculate verification bonus points:
        - 1 device: baseline 0 bonus
        - 2 devices: +12 pts
        - 3-4 devices: +18 pts
        - >=5 devices: +25 pts (max)
        """
        if unique_devices <= 1:
            return 0
        elif unique_devices == 2:
            return 12
        elif unique_devices in (3, 4):
            return 18
        else:
            return 25

    async def evaluate_swarm_consensus(
        self,
        session: AsyncSession,
        current_lat: Optional[float],
        current_lng: Optional[float],
        current_device_id: Optional[str] = None,
        exclude_report_id: Optional[Any] = None,
        radius_meters: float = 500.0,
        time_window_minutes: int = 15,
    ) -> SwarmConsensusResult:
        """
        Query database for active co-located reports from distinct devices within 500m / 15m.
        """
        if current_lat is None or current_lng is None:
            cd = self.compute_cluster_density(1)
            return SwarmConsensusResult(
                cluster_density_factor=cd,
                unique_devices_count=1,
                total_corroborating_reports=1,
                swarm_consensus_achieved=False,
                cluster_bonus_pts=0,
                cluster_score=0.25,
                flags=["SWARM_NO_GPS_BASELINE"],
            )

        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)

        try:
            from app.models.report import Report
            from app.api.routes.reports import _extract_lat_lng

            stmt = select(Report).where(
                and_(
                    Report.created_at >= cutoff_time,
                    Report.status.notin_(["rejected", "false_alarm"]),
                )
            )
            if exclude_report_id:
                stmt = stmt.where(Report.id != exclude_report_id)

            res = await session.execute(stmt)
            recent_reports = res.scalars().all()

            unique_devices = set()
            if current_device_id:
                unique_devices.add(current_device_id)

            corroborating_count = 1  # Include self
            flags = []

            for rep in recent_reports:
                coords = _extract_lat_lng(rep.gps_location)
                if not coords:
                    continue
                dist_m = _haversine_distance_m(current_lat, current_lng, coords[0], coords[1])
                if dist_m <= radius_meters:
                    corroborating_count += 1
                    # Extract unique device identifier
                    dev_id = getattr(rep, "device_fingerprint", None) or getattr(rep, "user_id", None) or str(rep.id)
                    unique_devices.add(str(dev_id))

            n_devices = max(1, len(unique_devices))
            cd = self.compute_cluster_density(n_devices)
            swarm_achieved = n_devices >= 2
            bonus_pts = self.calculate_swarm_bonus(cd, n_devices)

            if swarm_achieved:
                flags.append(f"SWARM_CONSENSUS_CONFIRMED({n_devices}_devices_in_{int(radius_meters)}m)")
            else:
                flags.append("SWARM_ISOLATED_SINGLE_SIGNAL")

            norm_score = min(1.0, round(cd / 2.5, 3))

            return SwarmConsensusResult(
                cluster_density_factor=cd,
                unique_devices_count=n_devices,
                total_corroborating_reports=corroborating_count,
                swarm_consensus_achieved=swarm_achieved,
                cluster_bonus_pts=bonus_pts,
                cluster_score=norm_score,
                flags=flags,
            )

        except Exception as e:
            print(f"[SwarmConsensus] Warning during swarm evaluation: {e}")
            cd = self.compute_cluster_density(1)
            return SwarmConsensusResult(
                cluster_density_factor=cd,
                unique_devices_count=1,
                total_corroborating_reports=1,
                swarm_consensus_achieved=False,
                cluster_bonus_pts=0,
                cluster_score=0.25,
                flags=["SWARM_EVALUATION_FALLBACK"],
            )

    async def evaluate_spatiotemporal_consensus(
        self,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_meters: float = 500.0,
        time_window_minutes: int = 15,
        exclude_report_id: Optional[Any] = None,
        device_id: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Adapter method for async verification pipeline.
        Can run with an existing session or create an ad-hoc session via async_session_maker.
        """
        if session is not None:
            res = await self.evaluate_swarm_consensus(
                session=session,
                current_lat=lat,
                current_lng=lng,
                current_device_id=device_id,
                exclude_report_id=exclude_report_id,
                radius_meters=radius_meters,
                time_window_minutes=time_window_minutes,
            )
        else:
            try:
                from app.db.database import async_session_maker
                async with async_session_maker() as new_session:
                    res = await self.evaluate_swarm_consensus(
                        session=new_session,
                        current_lat=lat,
                        current_lng=lng,
                        current_device_id=device_id,
                        exclude_report_id=exclude_report_id,
                        radius_meters=radius_meters,
                        time_window_minutes=time_window_minutes,
                    )
            except Exception as e:
                cd = self.compute_cluster_density(1)
                res = SwarmConsensusResult(
                    cluster_density_factor=cd,
                    unique_devices_count=1,
                    total_corroborating_reports=1,
                    swarm_consensus_achieved=False,
                    cluster_bonus_pts=0,
                    cluster_score=0.25,
                    flags=[f"SWARM_SESSION_ERROR: {str(e)[:50]}"],
                )

        return {
            "corroborated": res.swarm_consensus_achieved,
            "unique_devices_count": res.unique_devices_count,
            "total_corroborating_reports": res.total_corroborating_reports,
            "cluster_density_factor": res.cluster_density_factor,
            "cluster_bonus": float(res.cluster_bonus_pts),
            "cluster_score": res.cluster_score,
            "cluster_id": None,
            "flags": res.flags,
        }


swarm_consensus_service = SwarmConsensusService()
