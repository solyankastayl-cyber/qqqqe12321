#!/bin/bash
# Fractal Backend Runner for Supervisor
cd /app/backend
export NODE_ENV=development
export PORT=8001
export FRACTAL_ONLY=1
export MINIMAL_BOOT=1
export FRACTAL_ENABLED=true
exec npx tsx src/app.fractal.ts
