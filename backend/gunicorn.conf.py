import os

# Bind to Render's PORT
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# Only 1 worker to save memory on free tier (512MB)
workers = 1
worker_class = "uvicorn.workers.UvicornWorker"

# Extended timeout for LLM requests
timeout = 120
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Preload app to save memory
preload_app = True

# Worker restart to prevent memory leaks
max_requests = 500
max_requests_jitter = 50

