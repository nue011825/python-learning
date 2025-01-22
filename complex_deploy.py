from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
from prefect.infrastructure.docker import DockerContainer
from prefect.filesystems import S3
from prefect.artifacts import create_markdown_artifact
from main_flow import main_flow
import json

# Infrastructure configuration
docker_block = DockerContainer(
    image="prefect-etl:latest",
    image_pull_policy="ALWAYS",
    auto_remove=True,
    network_mode="host",
    env={
        "PREFECT_LOGGING_LEVEL": "INFO",
        "EXTRA_PIP_PACKAGES": "s3fs>=2023.3.0 pandas>=1.5.3"
    }
)

# Storage configuration
s3_block = S3(
    bucket_path="prefect-flows/etl",
    boto3_session_kwargs={
        "profile_name": "prod",
        "region_name": "us-east-1"
    }
)

# Create multiple deployments for different scenarios
deployments = [
    {
        "name": "prod_daily_load",
        "schedule": CronSchedule(cron="0 2 * * *"),
        "tags": ["prod", "daily"],
        "parameters": {
            "configs": [
                {
                    "name": "products",
                    "pk_columns": ["product_id"],
                    "batch_size": 50000
                }
            ]
        }
    },
    {
        "name": "prod_hourly_incremental",
        "schedule": CronSchedule(cron="0 * * * *"),
        "tags": ["prod", "incremental"],
        "parameters": {
            "configs": [
                {
                    "name": "sales",
                    "pk_columns": ["sale_id"],
                    "incremental_column": "created_at",
                    "batch_size": 10000
                }
            ]
        }
    }
]

for dep_config in deployments:
    deployment = Deployment.build_from_flow(
        flow=main_flow,
        name=dep_config["name"],
        schedule=dep_config["schedule"],
        tags=dep_config["tags"],
        parameters=dep_config["parameters"],
        infrastructure=docker_block,
        storage=s3_block,
        work_queue_name="prod-etl",
        description=json.dumps({
            "owner": "data-engineering",
            "team": "etl",
            "slack_channel": "#etl-alerts"
        })
    )
    
    deployment.apply()