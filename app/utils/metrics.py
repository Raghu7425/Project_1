from prometheus_client import Counter, Gauge, Histogram

JOBS_SUBMITTED = Counter("jobs_submitted_total", "Total jobs submitted", ["job_type"])
JOBS_PROCESSED = Counter("jobs_processed_total", "Total jobs completed", ["job_type"])
JOBS_FAILED = Counter("jobs_failed_total", "Total jobs failed", ["job_type", "terminal"])
JOB_LATENCY = Histogram("worker_job_latency_seconds", "Worker job processing latency", ["job_type"])
QUEUE_LENGTH = Gauge("queue_length", "Redis stream queue length", ["priority"])
HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
