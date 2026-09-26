# ---------------------------------------------------------------------------
# Stage 1: build the static bundle with Node
# ---------------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies first so Docker can cache this layer.
COPY package*.json ./
RUN npm ci --no-audit --no-fund

# Copy the rest of the source and produce a production bundle.
COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: serve the bundle with nginx and reverse-proxy /api to the backend
# ---------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# SPA + API-proxy configuration.
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static assets produced by Vite.
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
