# Fractal Backend Entry Point
# FastAPI proxy to TypeScript Fractal server running on internal port 8002
import subprocess
import os
import sys
import signal
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# TypeScript server runs on internal port
TS_PORT = 8002
TS_URL = f"http://127.0.0.1:{TS_PORT}"

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
    print(f"[Proxy] TypeScript server started (PID: {ts_process.pid})")

def stop_typescript_server():
    """Stop TypeScript server"""
    global ts_process
    if ts_process:
        ts_process.terminate()
        try:
            ts_process.wait(timeout=5)
        except:
            ts_process.kill()
        print("[Proxy] TypeScript server stopped")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_typescript_server()
    # Wait for TS server to be ready
    for _ in range(60):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{TS_URL}/api/health", timeout=2.0)
                if resp.status_code == 200:
                    print("[Proxy] TypeScript server ready!")
                    break
        except:
            pass
        await asyncio.sleep(1)
    else:
        print("[Proxy] WARNING: TypeScript server not responding after 60s")
    
    yield
    
    # Shutdown
    stop_typescript_server()

app = FastAPI(title="Fractal Backend Proxy", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Proxy all /api/* requests to TypeScript
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_api(request: Request, path: str):
    url = f"{TS_URL}/api/{path}"
    query_string = str(request.query_params)
    if query_string:
        url = f"{url}?{query_string}"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            body = await request.body()
            headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
            
            resp = await client.request(
                method=request.method,
                url=url,
                content=body if body else None,
                headers=headers,
            )
            
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type"),
            )
        except httpx.TimeoutException:
            return JSONResponse({"error": "Request timeout"}, status_code=504)
        except httpx.ConnectError:
            return JSONResponse({"error": "TypeScript server unavailable", "url": url}, status_code=503)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

# Health check (direct)
@app.get("/health")
async def health():
    return {"ok": True, "proxy": "FastAPI", "backend": "TypeScript", "ts_port": TS_PORT}
