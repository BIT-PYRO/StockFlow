# ─────────────────────────────────────────────────────────────────
# Stage 1 – Build the React app
# ─────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer-cached unless package.json changes)
COPY package*.json ./
RUN npm ci --prefer-offline

# Build-time environment variables
# VITE_API_BASE_URL defaults to /api so nginx can proxy it;
# override at build time if you serve the API from a different path.
ARG  VITE_API_BASE_URL=/api
ENV  VITE_API_BASE_URL=$VITE_API_BASE_URL

# Copy source and build
COPY . .
RUN npm run build


# ─────────────────────────────────────────────────────────────────
# Stage 2 – Serve with nginx
# ─────────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Install curl for the healthcheck (BusyBox wget does not support -O-)
RUN apk add --no-cache curl

# Remove the default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy the Vite build output
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy the custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# curl -f returns exit code 22 on HTTP errors (4xx/5xx) and non-zero on
# connection failure — both correctly signal an unhealthy container.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f --silent --max-time 5 http://localhost/ > /dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
