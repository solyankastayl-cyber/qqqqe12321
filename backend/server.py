# Fractal Backend Entry Point
# Runs TypeScript Fractal server directly on port 8001
import subprocess
import os
import sys
import signal
import atexit

def run_typescript_server():
    """Run TypeScript Fractal server directly on port 8001"""
    env = os.environ.copy()
    env.update({
        "NODE_ENV": "development",
        "FRACTAL_ONLY": "1",
        "MINIMAL_BOOT": "1",
        "FRACTAL_ENABLED": "true",
        "PORT": "8001",
    })
    
    process = subprocess.Popen(
        ["npx", "tsx", "src/app.fractal.ts"],
        env=env,
        cwd="/app/backend",
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    def cleanup():
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()
    
    atexit.register(cleanup)
    
    def signal_handler(signum, frame):
        cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Wait for the process
    return process.wait()

if __name__ == "__main__":
    sys.exit(run_typescript_server())

# ASGI app is required but never used (uvicorn loads module, not main)
# TypeScript server handles all requests directly
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
async def root():
    return {"error": "This endpoint should never be called. TypeScript server runs on :8001"}
