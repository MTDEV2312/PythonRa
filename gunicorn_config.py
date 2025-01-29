# Gunicorn configuration file

# Servidor y Workers
worker_class = 'gevent'  # Usar gevent para manejo asíncrono
workers = 2              # Número de workers (procesos)
threads = 4             # Número de threads por worker
worker_connections = 1000  # Máximo número de conexiones simultáneas por worker

# Timeouts
timeout = 120           # Timeout en segundos para workers
keepalive = 5          # Tiempo en segundos para mantener conexiones abiertas
graceful_timeout = 30   # Tiempo para terminar workers gracefully

# Logging
loglevel = 'info'
accesslog = '-'         # '-' significa stdout
errorlog = '-'         # '-' significa stderr
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
bind = '0.0.0.0:5000'  # Puerto en el que escuchará gunicorn
backlog = 2048         # Número máximo de conexiones pendientes

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