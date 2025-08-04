from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from ipaddress import ip_address

# ALLOWED_IPS can stay as strings
ALLOWED_IPS = {
    "52.89.214.238",
    "34.212.75.30",
    "54.218.53.128",
    "52.32.178.7"
}

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            # Parse and normalize IP
            client_ip = str(ip_address(request.client.host))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid IP address")

        if client_ip not in ALLOWED_IPS:
            raise HTTPException(status_code=403, detail=f"Access denied from IP: {client_ip}")

        return await call_next(request)
