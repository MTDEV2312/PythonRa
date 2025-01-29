import os
from gevent import monkey
monkey.patch_all()

# Servidor y Workers
worker_class = 'gevent'
workers = 1  # Cambiamos a 1 worker para evitar problemas con los threads
threads = 4
worker_connections = 1000

# El resto de tu configuración igual...