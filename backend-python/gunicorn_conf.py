bind = "0.0.0.0:8000"
workers = 4  # start with 4 for 1,000-1,500 students; tune based on server CPU cores
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 60
