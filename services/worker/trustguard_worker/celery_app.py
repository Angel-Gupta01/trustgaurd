# services/worker/trustguard_worker/celery_app.py
import os
from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

app = Celery(
    "trustguard_worker",
    broker=broker_url,
    backend=result_backend,
    include=[
        "trustguard_worker.tasks.frame_extraction",
        "trustguard_worker.tasks.deepfake_orchestration",
        "trustguard_worker.tasks.blockchain_anchor",
        "trustguard_worker.tasks.tx_confirmation_poller",
    ]
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "frame_extraction.*": {"queue": "media_processing"},
        "deepfake_orchestration.*": {"queue": "inference_dispatch"},
        "blockchain_anchor.*": {"queue": "blockchain"},
        "tx_confirmation_poller.*": {"queue": "blockchain"},
    }
)
