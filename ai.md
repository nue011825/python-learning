# adv prefect implementation

# Advanced Prefect Implementation Guide

## Project Structure
```
prefect_etl/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── logging_config.py
├── flows/
│   ├── __init__.py
│   ├── main.py
│   ├── raw_data.py
│   └── transformations.py
├── tasks/
│   ├── __init__.py
│   ├── extraction.py
│   ├── loading.py
│   └── transformation.py
├── utils/
│   ├── __init__.py
│   ├── metrics.py
│   └── validation.py
├── deployments/
│   ├── __init__.py
│   └── production.py
└── tests/
    ├── __init__.py
    ├── test_flows.py
    └── test_tasks.py
```

## Core Implementation Features

### 1. Dynamic Task Generation
```python
from prefect import task, flow
from typing import List, Dict
import asyncio

@task
async def process_partition(data: pd.DataFrame) -> Dict:
    return {"processed": len(data)}

@flow
async def dynamic_processing(data: pd.DataFrame, partition_size: int = 1000):
    partitions = [data[i:i+partition_size] 
                 for i in range(0, len(data), partition_size)]
    
    results = await asyncio.gather(
        *[process_partition.submit(partition) for partition in partitions]
    )
    
    return sum(r["processed"] for r in results)
```

### 2. Advanced State Management
```python
from prefect import task
from prefect.tasks import Task
from datetime import timedelta

@task(
    retries=3,
    retry_delay_seconds=30,
    cache_key_fn=lambda context, *args, **kwargs: 
        f"{context.task_run.name}:{args[0]}",
    cache_expiration=timedelta(hours=1)
)
async def cached_data_fetch(query_id: str) -> pd.DataFrame:
    # Implementation with caching and retry logic
    pass
```

### 3. Resource Management
```python
from prefect.tasks import task_input_hash
from prefect.utilities.resources import ResourceManager

class DatabaseConnection(ResourceManager):
    def __init__(self, connection_params: Dict):
        self.params = connection_params
        self._conn = None

    async def setup(self):
        self._conn = await create_connection(self.params)
        return self._conn

    async def cleanup(self):
        if self._conn:
            await self._conn.close()

@task(retries=3, cache_key_fn=task_input_hash)
async def database_operation():
    async with DatabaseConnection(connection_params) as conn:
        # Guaranteed cleanup after operation
        pass
```

### 4. Advanced Monitoring
```python
from prefect import flow
from prefect.utilities.annotations import metrics

@flow(
    name="monitored_flow",
    track_metrics=True
)
async def monitored_flow():
    with metrics.timer("processing_time"):
        result = await process_data()
    
    metrics.gauge(
        "records_processed",
        len(result),
        tags={"environment": "production"}
    )
```

### 5. Subflow Orchestration
```python
from prefect import flow
from typing import List

@flow
async def child_flow(data: pd.DataFrame) -> Dict:
    return {"processed": len(data)}

@flow
async def parent_flow(datasets: List[pd.DataFrame]):
    results = []
    for dataset in datasets:
        if len(dataset) > 1000:
            # Spawn subflow for large datasets
            result = await child_flow(dataset)
        else:
            # Process small datasets directly
            result = await process_data(dataset)
        results.append(result)
    return results
```

### 6. Advanced Error Handling
```python
from prefect import flow, task
from prefect.utilities.exceptions import PrefectException

class DataValidationError(PrefectException):
    """Custom error for data validation failures"""
    pass

@task(
    retries=3,
    retry_delay_seconds=exponential_backoff(backoff_factor=60),
    retry_jitter_factor=0.1
)
async def validate_data(data: pd.DataFrame):
    if data.isnull().any().any():
        raise DataValidationError("Data contains null values")
    return data

@flow(
    validate_parameters=True,
    version="1.0.0"
)
async def validation_flow(data: pd.DataFrame):
    try:
        validated_data = await validate_data(data)
        return await process_data(validated_data)
    except DataValidationError as e:
        await handle_validation_error(e)
        raise
```