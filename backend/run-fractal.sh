#!/bin/bash
cd /app/backend
export NODE_ENV=development
export FRACTAL_ONLY=1
export MINIMAL_BOOT=1
export FRACTAL_ENABLED=true

# Load env
set -a
source .env
set +a

exec npx tsx src/app.fractal.ts
