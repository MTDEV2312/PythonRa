import os

# Servidor y Workers
worker_class = 'gevent'
workers = 2
threads = 4
worker_connections = 1000

# Timeouts
timeout = 120
keepalive = 5
graceful_timeout = 30

# Logging
loglevel = 'info'
accesslog = '-'
errorlog = '-'
access_log_format = '%({x-real-ip}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Buffer
limit_request_line = 0
limit_request_fields = 32768
limit_request_field_size = 0

# Server Mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Server Socket
port = int(os.environ.get('PORT', 5000))
bind = f'0.0.0.0:{port}'
backlog = 2048

# SSL
keyfile = None
certfile = None

# Process Naming
proc_name = None

# Server Hooks
def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal")