# frontend.Dockerfile — FALLBACK Node image for the FINARODA frontend on Railway.
#
# The RECOMMENDED path is the Node-only nixpacks build (frontend/nixpacks.toml,
# Root Directory = "frontend"). Use THIS Dockerfile only if you specifically want a
# Docker build.
#
# ⚠️ This must be built with the REPO ROOT as the build context (so it can COPY both
# `shared/` and `frontend/`). On Railway that means the frontend service's
# Root Directory = "/" and `RAILWAY_DOCKERFILE_PATH=frontend.Dockerfile`. Note: with
# Root Directory "/", the service also reads the repo-root railway.toml — you MUST
# clear its Healthcheck Path (it is `/api/health`, the backend's) in the service
# settings, or the frontend deploy will be marked unhealthy.
#
# pnpm is installed via npm (NOT corepack) to avoid the corepack keyid error.

FROM node:22.12.0-bookworm-slim

# Direct pnpm install — no corepack (sidesteps the "Cannot find matching keyid" error).
RUN npm install -g pnpm@10.33.1

WORKDIR /app

# Build context = repo root → the shared engine and the frontend are both copied,
# so `link:../shared` (frontend → ../shared) resolves to /app/shared.
COPY shared/ ./shared/
COPY frontend/ ./frontend/

WORKDIR /app/frontend

# NEXT_PUBLIC_* are inlined at BUILD time — Railway passes service vars as build args.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1

RUN pnpm install --no-frozen-lockfile
RUN pnpm build

EXPOSE 8080
# Railway sets $PORT at runtime.
CMD ["sh", "-c", "pnpm exec next start -p ${PORT:-8080}"]
