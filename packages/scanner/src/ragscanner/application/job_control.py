"""Use cases for durable job creation, inspection, cancellation, and retry."""

from pathlib import Path

from ragscanner.ai_analysis import AIProviderConfig
from ragscanner.application.static_scan import StaticScanJobPayload
from ragscanner.connectors import OpenWebUISourceConfig
from ragscanner.jobs import (
    JobKind,
    JobNotFoundError,
    JobPage,
    JobRecord,
    JobRepository,
    JobRequest,
)


class JobApplicationService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    def enqueue_local_scan(
        self,
        path: Path,
        *,
        config_path: Path | None = None,
        idempotency_key: str | None = None,
        max_attempts: int = 3,
        ai_config: AIProviderConfig | None = None,
        source_name: str | None = None,
    ) -> JobRecord:
        resolved_path = path.expanduser().resolve(strict=True)
        if resolved_path == Path(resolved_path.anchor):
            raise ValueError("filesystem root cannot be used as an unrestricted scan root")
        resolved_config = config_path.expanduser().resolve(strict=True) if config_path else None
        payload = StaticScanJobPayload(
            source_kind="local",
            path=str(resolved_path),
            config_path=str(resolved_config) if resolved_config else None,
            ai=ai_config or AIProviderConfig(),
            source_name=source_name or resolved_path.name,
        )
        return self.repository.enqueue(
            JobRequest(
                kind=JobKind.SCAN,
                payload=payload.model_dump(mode="json", exclude_none=True),
                idempotency_key=idempotency_key,
                max_attempts=max_attempts,
            )
        )

    def enqueue_openwebui_scan(
        self,
        *,
        base_url: str,
        knowledge_id: str,
        credential_ref: str,
        content_consent: bool,
        idempotency_key: str | None = None,
        max_attempts: int = 3,
        ai_config: AIProviderConfig | None = None,
        source_name: str | None = None,
    ) -> JobRecord:
        OpenWebUISourceConfig(
            base_url=base_url,
            knowledge_id=knowledge_id,
            credential_ref=credential_ref,
            content_consent=content_consent,
        )
        payload = StaticScanJobPayload(
            source_kind="openwebui",
            openwebui_base_url=base_url,
            openwebui_knowledge_id=knowledge_id,
            credential_ref=credential_ref,
            content_consent=content_consent,
            ai=ai_config or AIProviderConfig(),
            source_name=source_name or f"OpenWebUI · {knowledge_id}",
        )
        return self.repository.enqueue(
            JobRequest(
                kind=JobKind.SCAN,
                payload=payload.model_dump(mode="json", exclude_none=True),
                idempotency_key=idempotency_key,
                max_attempts=max_attempts,
            )
        )

    def get(self, job_id: str) -> JobRecord:
        job = self.repository.get(job_id)
        if job is None:
            raise JobNotFoundError("The requested job does not exist.")
        return job

    def list(self, *, limit: int = 50, offset: int = 0) -> JobPage:
        return self.repository.list(limit=limit, offset=offset)

    def cancel(self, job_id: str) -> JobRecord:
        return self.repository.request_cancellation(job_id)

    def retry(self, job_id: str) -> JobRecord:
        return self.repository.retry(job_id)
