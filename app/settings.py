import os

DD_URL = os.environ["DD_URL"]
DD_TOKEN = os.environ["DD_TOKEN"]
GIT_DOMAIN = os.environ["GIT_DOMAIN"]

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_REPORT_SIZE_MB = int(os.getenv("MAX_REPORT_SIZE_MB", "20"))
