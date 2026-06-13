from typing import Protocol, runtime_checkable

from journey.models import WorkerRequest, WorkerResponse


@runtime_checkable
class JourneyWorker(Protocol):
    worker_name: str

    def execute(self, request: WorkerRequest) -> WorkerResponse: ...
