from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
from snowflake_etl import main_flow
#prefect deployment configuration
deployment = Deployment.build_from_flow(
    flow=main_flow,
    name="retail_etl_pipeline",
    schedule=CronSchedule(cron="0 2 * * *"),  # Runs daily at 2 AM
    work_queue_name="snowflake-etl",
    tags=["snowflake", "retail"]
)

if __name__ == "__main__":
    deployment.apply()