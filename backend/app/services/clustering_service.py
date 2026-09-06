from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from app.config import settings

class ClusteringService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def cluster_reports(self) -> List[Dict[str, Any]]:
        sql = """
        WITH clustered AS (
            SELECT
                r.id,
                r.ai_extraction,
                r.gps_location,
                r.confidence_score,
                ST_ClusterDBSCAN(
                    ST_Transform(r.gps_location::geometry, 32642),
                    eps := :radius,
                    minpoints := :min_size
                ) OVER () AS cid
            FROM reports r
            WHERE r.status IN ('pending', 'verified')
              AND r.created_at > NOW() - (INTERVAL '1 hour' * :time_window)
              AND r.confidence_score > 0.3
        )
        SELECT
            c.cid::INT AS cluster_id,
            ARRAY_AGG(c.id) AS report_ids,
            ST_AsText(ST_Centroid(ST_Collect(c.gps_location::geometry))) AS centroid,
            COUNT(*)::INT AS total_reports,
            COALESCE(SUM((c.ai_extraction->>'headcount')::INT), COUNT(*))::INT AS total_individuals,
            ARRAY_AGG(DISTINCT c.ai_extraction->>'hazard_type') AS hazard_types,
            AVG(c.confidence_score)::FLOAT AS avg_confidence,
            jsonb_agg(DISTINCT c.ai_extraction->'medical_risks') FILTER (
                WHERE c.ai_extraction->'medical_risks' IS NOT NULL
            ) AS medical_risks
        FROM clustered c
        WHERE c.cid IS NOT NULL
        GROUP BY c.cid;
        """
        
        result = await self.session.execute(text(sql), {
            "radius": settings.clustering_radius_meters,
            "min_size": settings.clustering_min_size,
            "time_window": settings.clustering_time_window_hours
        })
        
        clusters = []
        for row in result:
            clusters.append({
                "cluster_id": row.cluster_id,
                "report_ids": row.report_ids,
                "centroid": row.centroid,
                "total_reports": row.total_reports,
                "total_individuals": row.total_individuals,
                "hazard_types": row.hazard_types,
                "avg_confidence": row.avg_confidence,
                "medical_risks": row.medical_risks
            })
            
        return clusters

    async def find_and_attach_nearby_parent(
        self,
        report_id: Any,
        lat: float,
        lng: float,
        radius_meters: float = 150.0,
        time_window_hours: int = 12,
    ) -> Optional[Any]:
        """
        Cluster incoming reports within a 150m radius and 12-hour window.
        Attaches duplicate/corroborating signals as child references to the parent report,
        incrementing corroborated_count and boosting confidence score.
        """
        query = text("""
            SELECT id, confidence_score, corroborated_count
            FROM reports
            WHERE id != :report_id
              AND parent_report_id IS NULL
              AND gps_location IS NOT NULL
              AND status NOT IN ('rejected', 'false_alarm')
              AND created_at > NOW() - (INTERVAL '1 hour' * :time_window)
              AND ST_DistanceSphere(gps_location::geometry, ST_SetSRID(ST_Point(:lng, :lat), 4326)) <= :radius
            ORDER BY ST_DistanceSphere(gps_location::geometry, ST_SetSRID(ST_Point(:lng, :lat), 4326)) ASC
            LIMIT 1;
        """)

        res = await self.session.execute(query, {
            "report_id": report_id,
            "lng": lng,
            "lat": lat,
            "radius": radius_meters,
            "time_window": time_window_hours,
        })
        parent_row = res.mappings().first()
        if not parent_row:
            return None

        parent_id = parent_row["id"]
        old_conf = parent_row["confidence_score"] or 0.5
        new_conf = min(1.0, round(old_conf + 0.1, 2))
        old_count = parent_row["corroborated_count"] or 1
        new_count = old_count + 1

        # Update parent report
        await self.session.execute(
            text("""
                UPDATE reports
                SET corroborated_count = :count,
                    confidence_score = :conf
                WHERE id = :pid
            """),
            {"count": new_count, "conf": new_conf, "pid": parent_id}
        )

        # Update child report
        await self.session.execute(
            text("""
                UPDATE reports
                SET parent_report_id = :pid
                WHERE id = :rid
            """),
            {"pid": parent_id, "rid": report_id}
        )
        await self.session.commit()
        return parent_id

from fastapi import Depends
from app.db.database import get_db

async def get_clustering_service(session: AsyncSession = Depends(get_db)) -> ClusteringService:
    return ClusteringService(session)

