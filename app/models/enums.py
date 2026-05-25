from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(StrEnum):
    DOCUMENT_OCR = "document_ocr"
    MEDIA_TRANSCODE = "media_transcode"
    AI_SUMMARIZATION = "ai_summarization"
    CONTENT_MODERATION = "content_moderation"
