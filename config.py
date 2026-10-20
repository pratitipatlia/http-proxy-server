# Shared configuration for the HTTP Proxy Server

HOST = "127.0.0.1"
PORT = 8080

DEFAULT_CACHE_TTL = 60       # seconds
CONNECTION_TIMEOUT = 10      # seconds
BUFFER_SIZE = 8192

BLOCKED_DOMAINS = [
    "example.com"
]