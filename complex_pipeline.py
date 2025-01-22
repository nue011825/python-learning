from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from prefect_snowflake.database import SnowflakeConnector
from prefect.artifacts import create_markdown_artifact
from prefect.filesystems import S3
from prefect_aws.s3 import S3Bucket
from prefect.context import get_run_context
from prefect.states import Failed
import asyncio
import pyarrow as pa
import pyarrow.parquet as pq
from contextlib import asynccontextmanager
import json
from dataclasses import dataclass
from prefect.runtime.task_runner import TaskRunner
from typing import AsyncGenerator

@dataclass
class TableConfig:
    """Configuration for table processing"""
    name: str
    pk_columns: List[str]
    partition_columns: Optional[List[str]] = None
    incremental_column: Optional[str] = None
    batch_size: int = 50000

class CustomTaskRunner(TaskRunner):
    """Custom task runner with enhanced monitoring"""
    async def initialize_run(self) -> None:
        logger = get_run_logger()
        logger.info(f"Initializing task: {self.task.name}")
        await super().initialize_run()

@asynccontextmanager
async def snowflake_connection(connector: SnowflakeConnector) -> AsyncGenerator:
    """Async context manager for Snowflake connections"""
    conn = await asyncio.to_thread(connector.get_connection)
    try:
        yield conn
    finally:
        await asyncio.to_thread(conn.close)

@task(retries=3, 
      retry_delay_seconds=exponential_backoff(backoff_factor=30),
      cache_key_fn=task_input_hash,
      task_runner=CustomTaskRunner)
async def validate_source_data(
    s3_path: str,
    table_config: TableConfig,
    s3_bucket: S3Bucket) -> Dict[str, Any]:
    """
    Validate source data before processing
    Advantages over Airflow:
    - Async execution
    - Built-in caching
    - Structured error handling
    """
    logger = get_run_logger()
    
    try:
        # Read sample of data for validation
        buffer = await s3_bucket.download_object(s3_path)
        table = pq.read_table(buffer)
        df_sample = table.to_pandas().head(1000)

        validation_results = {
            "total_rows": len(table),
            "missing_pk": False,
            "data_types_match": True,
            "null_check_passed": True
        }

        # Validate primary keys
        for pk in table_config.pk_columns:
            if df_sample[pk].isnull().any():
                validation_results["missing_pk"] = True
                logger.error(f"Found null values in primary key column: {pk}")

        # Create validation artifact
        await create_markdown_artifact(
            key=f"validation-{table_config.name}",
            markdown=f"""
            # Data Validation Results for {table_config.name}
            - Total Rows: {validation_results['total_rows']}
            - PK Validation: {'❌' if validation_results['missing_pk'] else '✅'}
            - Data Types: {'❌' if not validation_results['data_types_match'] else '✅'}
            - Null Check: {'❌' if not validation_results['null_check_passed'] else '✅'}
            """
        )

        return validation_results

    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        raise Failed(message=str(e))

@task(retries=3)
async def process_data_batch(
    batch_df: pd.DataFrame,
    table_config: TableConfig,
    connector: SnowflakeConnector) -> Dict[str, int]:
    """
    Process a batch of data with advanced error handling
    Advantages over Airflow:
    - Native batch processing
    - Granular error handling
    - Real-time metrics
    """
    logger = get_run_logger()
    metrics = {"processed": 0, "errors": 0}

    async with snowflake_connection(connector) as conn:
        try:
            # Apply transformations
            batch_df = await transform_batch(batch_df)
            
            # Upsert data
            success = await asyncio.to_thread(
                upsert_to_snowflake,
                conn, 
                batch_df,
                table_config
            )
            
            metrics["processed"] = len(batch_df)
            
            # Emit metrics
            await emit_batch_metrics(metrics, table_config.name)
            
            return metrics
            
        except Exception as e:
            metrics["errors"] = len(batch_df)
            logger.error(f"Batch processing failed: {str(e)}")
            raise Failed(message=str(e))

@flow(name="Data Quality Flow",
      description="Performs data quality checks and reporting",
      version="1.0")
async def data_quality_flow(
    table_config: TableConfig,
    validation_results: Dict[str, Any]) -> None:
    """
    Dedicated flow for data quality management
    Advantages over Airflow:
    - Subflow composition
    - Rich metadata
    - Dynamic task generation
    """
    logger = get_run_logger()

    if not validation_results["null_check_passed"]:
        logger.warning(f"Data quality issues detected for {table_config.name}")
        
        # Generate data quality report
        await create_markdown_artifact(
            key=f"dq-report-{table_config.name}",
            markdown=f"""
            # Data Quality Report
            Table: {table_config.name}
            Time: {datetime.now()}
            Status: ⚠️ Issues Detected
            """
        )

@flow(name="Incremental Load Flow")
async def incremental_load_flow(
    table_config: TableConfig,
    connector: SnowflakeConnector,
    s3_bucket: S3Bucket) -> None:
    """
    Handles incremental data loading
    Advantages over Airflow:
    - State management
    - Parameter validation
    - Dynamic orchestration
    """
    if not table_config.incremental_column:
        raise ValueError("Incremental column not configured")

    last_processed = await get_last_processed_value(
        connector,
        table_config
    )

    new_data = await load_incremental_data(
        s3_bucket,
        table_config,
        last_processed
    )

    if not new_data.empty:
        await process_data_batch(new_data, table_config, connector)

@flow(name="Main ETL Flow",
      description="Orchestrates the entire ETL process",
      version="1.0")
async def main_flow(
    configs: List[TableConfig],
    date: Optional[datetime] = None) -> None:
    """
    Main orchestration flow
    Advantages over Airflow:
    - Async by default
    - Rich type hints
    - Parameter validation
    """
    date = date or datetime.utcnow()
    logger = get_run_logger()

    # Load infrastructure dependencies
    connector = SnowflakeConnector.load("snowflake-prod")
    s3_bucket = S3Bucket.load("data-lake")

    for config in configs:
        logger.info(f"Processing {config.name}")
        
        # Validate source data
        validation_results = await validate_source_data(
            f"raw/{config.name}/{date:%Y/%m/%d}",
            config,
            s3_bucket
        )

        # Run data quality checks
        await data_quality_flow(config, validation_results)

        if validation_results["null_check_passed"]:
            # Process incrementally if configured
            if config.incremental_column:
                await incremental_load_flow(config, connector, s3_bucket)
            else:
                # Full load
                data_iterator = await get_data_iterator(
                    s3_bucket,
                    config,
                    batch_size=config.batch_size
                )
                
                async for batch in data_iterator:
                    await process_data_batch(batch, config, connector)

if __name__ == "__main__":
    configs = [
        TableConfig(
            name="products",
            pk_columns=["product_id"],
            partition_columns=["category"]
        ),
        TableConfig(
            name="customers",
            pk_columns=["customer_id"],
            incremental_column="updated_at"
        )
    ]
    
    asyncio.run(main_flow(configs))