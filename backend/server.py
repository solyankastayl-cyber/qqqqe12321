# Fractal Backend Entry Point
# FastAPI proxy to TypeScript Fractal server running on internal port
import subprocess
import os
import sys
import signal
import threading
import time
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# TypeScript server runs on internal port
TS_PORT = 8002
TS_URL = f"http://127.0.0.1:{TS_PORT}"

app = FastAPI(title="Fractal Backend Proxy")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global TypeScript process
ts_process = None

def start_typescript_server():
    """Start TypeScript Fractal server in background"""
    global ts_process
    
    env = os.environ.copy()
    env.update({
        "NODE_ENV": "development",
        "FRACTAL_ONLY": "1",
        "MINIMAL_BOOT": "1",
        "FRACTAL_ENABLED": "true",
        "PORT": str(TS_PORT),
    })
    
    ts_process = subprocess.Popen(
        ["npx", "tsx", "src/app.fractal.ts"],
        env=env,
        cwd="/app/backend",
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    print(f"[Proxy] TypeScript server started on port {TS_PORT}")

def shutdown_typescript_server():
    """Shutdown TypeScript server"""
    global ts_process
    if ts_process:
        ts_process.terminate()
        ts_process.wait()
        print("[Proxy] TypeScript server stopped")

# Start TypeScript on app startup
@app.on_event("startup")
async def startup_event():
    threading.Thread(target=start_typescript_server, daemon=True).start()
    # Wait for TS server to be ready
    for _ in range(30):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{TS_URL}/api/health", timeout=2.0)
                if resp.status_code == 200:
                    print("[Proxy] TypeScript server ready")
                    return
        except:
            pass
        time.sleep(1)
    print("[Proxy] WARNING: TypeScript server not responding")

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_typescript_server()

# Handle signals
def signal_handler(signum, frame):
    shutdown_typescript_server()
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Proxy all /api/* requests to TypeScript
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_api(request: Request, path: str):
    url = f"{TS_URL}/api/{path}"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Build request
            body = await request.body()
            headers = dict(request.headers)
            headers.pop("host", None)
            
            # Forward request
            resp = await client.request(
                method=request.method,
                url=url,
                content=body if body else None,
                headers=headers,
                params=dict(request.query_params),
            )
            
            # Return response
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type=resp.headers.get("content-type"),
            )
        except httpx.TimeoutException:
            return JSONResponse({"error": "Request timeout"}, status_code=504)
        except httpx.ConnectError:
            return JSONResponse({"error": "TypeScript server unavailable"}, status_code=503)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

# Health check
@app.get("/health")
async def health():
    return {"ok": True, "proxy": "FastAPI", "backend": "TypeScript"}
