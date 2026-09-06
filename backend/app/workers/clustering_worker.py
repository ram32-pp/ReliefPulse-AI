import asyncio
from app.db.database import async_session_maker
from app.services.clustering_service import ClusteringService
from app.services.incident_service import IncidentService

async def run_clustering_job():
    while True:
        try:
            print("Running clustering job...")
            async with async_session_maker() as session:
                clustering_service = ClusteringService(session)
                incident_service = IncidentService(session)
                
                clusters = await clustering_service.cluster_reports()
                for cluster in clusters:
                    await incident_service.merge_reports_into_incident(cluster["report_ids"], cluster)
                    
            print(f"Clustering job completed. Found {len(clusters)} clusters.")
        except Exception as e:
            print(f"Error in clustering job: {e}")
            
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_clustering_job())
