from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(StrEnum):
    PDF_PROCESSING = "pdf_processing"
    IMAGE_RESIZE = "image_resize"
    EMAIL_SENDING = "email_sending"
    REPORT_GENERATION = "report_generation"
