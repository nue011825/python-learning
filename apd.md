# Advanced Prefect Deployment & Scheduling Guide

## Deployment Configurations

### 1. Production Deployment
```python
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
from prefect.infrastructure.container import DockerContainer
from prefect.filesystems import S3

# Infrastructure
docker_block = DockerContainer(
    image="my-etl-image:latest",
    image_pull_policy="Always",
    env={"ENVIRONMENT": "production"},
    memory_limit="4g",
    cpu_limit=2.0
)

# Storage
s3_block = S3(
    bucket_path="my-etl-storage",
    aws_access_key_id="key",
    aws_secret_access_key="secret"
)

# Deployment
deployment = Deployment.build_from_flow(
    flow=main_flow,
    name="production_etl",
    version="1.0.0",
    schedule=CronSchedule(cron="0 */4 * * *"),
    tags=["production", "etl"],
    infrastructure=docker_block,
    storage=s3_block,
    work_queue_name="production-queue",
    parameters={
        "batch_size": 10000,
        "parallel_tasks": 4
    }
)
```

### 2. Dynamic Scheduling
```python
from prefect.schedules import IntervalSchedule
from datetime import timedelta
import pendulum

def dynamic_interval():
    """Adjust schedule based on time of day"""
    now = pendulum.now()
    if 8 <= now.hour < 18:  # Business hours
        return timedelta(minutes=15)
    return timedelta(hours=1)

schedule = IntervalSchedule(
    interval=dynamic_interval,
    anchor_date=pendulum.datetime(2024, 1, 1),
    timezone="UTC"
)
```

### 3. Resource-Aware Scheduling
```python
from prefect.infrastructure import Process
from prefect.utilities.resources import ResourceManager

class ResourceAwareScheduler:
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._active = 0

    async def can_schedule(self) -> bool:
        # Check system resources
        cpu_usage = await get_cpu_usage()
        memory_usage = await get_memory_usage()
        
        return (
            self._active < self.max_concurrent and
            cpu_usage < 80 and
            memory_usage < 85
        )

    async def schedule_flow(self, flow_name: str):
        if await self.can_schedule():
            self._active += 1
            try:
                await run_flow(flow_name)
            finally:
                self._active -= 1
```

### 4. Advanced Work Queues
```python
from prefect.work_queues import WorkQueue

# Priority queue for critical jobs
critical_queue = WorkQueue(
    name="critical",
    priority=100,
    concurrency_limit=2,
    tags=["critical"]
)

# Standard queue for regular jobs
standard_queue = WorkQueue(
    name="standard",
    priority=50,
    concurrency_limit=5
)

# Batch queue for large jobs
batch_queue = WorkQueue(
    name="batch",
    priority=10,
    concurrency_limit=3,
    tags=["batch"]
)
```

### 5. Monitoring & Alerting
```python
from prefect.utilities.notifications import notify_on_failure
from prefect.tasks import Task
from typing import Optional

class MonitoredTask(Task):
    def __init__(
        self,
        name: str,
        alert_threshold: Optional[float] = None,
        **kwargs
    ):
        self.alert_threshold = alert_threshold
        super().__init__(name=name, **kwargs)

    @notify_on_failure(channel="slack")
    async def __call__(self, *args, **kwargs):
        start_time = time.time()
        result = await super().__call__(*args, **kwargs)
        duration = time.time() - start_time

        if (
            self.alert_threshold and 
            duration > self.alert_threshold
        ):
            await send_alert(
                f"Task {self.name} exceeded threshold: {duration}s"
            )

        return result
```

### 6. Deployment Automation
```python
import yaml
from prefect.utilities.asyncio import sync_compatible
from typing import Dict

class DeploymentAutomator:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    @sync_compatible
    async def create_deployments(self):
        for deployment_config in self.config["deployments"]:
            deployment = await self._create_deployment(
                deployment_config
            )
            await deployment.apply()

    async def _create_deployment(
        self, 
        config: Dict
    ) -> Deployment:
        infrastructure = await self._setup_infrastructure(
            config["infrastructure"]
        )
        storage = await self._setup_storage(
            config["storage"]
        )
        
        return Deployment.build_from_flow(
            flow=import_flow(config["flow_path"]),
            name=config["name"],
            schedule=self._create_schedule(config["schedule"]),
            infrastructure=infrastructure,
            storage=storage,
            work_queue_name=config["work_queue"],
            tags=config.get("tags", [])
        )
```

## Advanced Features

### 1. Custom Task Runners
```python
from prefect.task_runners import BaseTaskRunner
from prefect.utilities.collections import visit_collection

class OptimizedTaskRunner(BaseTaskRunner):
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers
        super().__init__()

    async def submit(self, task, *args, **kwargs):
        # Custom task submission logic
        pass

    async def wait(self, futures):
        # Custom wait logic
        pass
```

### 2. State Handlers
```python
from prefect import flow, task
from prefect.utilities.states import StateHandler

class CustomStateHandler(StateHandler):
    async def before_run(self, task, state):
        # Pre-run logic
        pass

    async def after_run(self, task, state, result):
        # Post-run logic
        pass

@task(state_handlers=[CustomStateHandler()])
async def monitored_task():
    # Task implementation
    pass
```