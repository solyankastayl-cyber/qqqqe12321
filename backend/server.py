# Fractal Backend Entry Point
# This file spawns the TypeScript Fractal server
import subprocess
import os
import sys
import time
import signal

def run_typescript_server():
    """Run the TypeScript Fractal server directly"""
    os.chdir("/app/backend")
    
    env = os.environ.copy()
    env.update({
        "NODE_ENV": "development",
        "FRACTAL_ONLY": "1",
        "MINIMAL_BOOT": "1",
        "FRACTAL_ENABLED": "true",
    })
    
    # Run TypeScript server
    process = subprocess.Popen(
        ["npx", "tsx", "src/app.fractal.ts"],
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    def signal_handler(signum, frame):
        process.terminate()
        process.wait()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Wait for the process
    process.wait()

if __name__ == "__main__":
    run_typescript_server()
