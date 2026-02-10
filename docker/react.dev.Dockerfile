# Multi-stage Dockerfile for React frontend with hot-reload support

# Base stage for Node.js
FROM node:20-alpine AS base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    curl \
    git

# Development stage with hot-reload
FROM base AS development

# Set environment to development
ENV NODE_ENV=development

# Copy package files
COPY src/react-frontend/package*.json ./

# Install all dependencies including dev dependencies
RUN npm ci --legacy-peer-deps

# Copy application code
COPY src/react-frontend/ ./

# Create non-root user for security
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose React development server port
EXPOSE 3000

# Expose webpack dev server websocket port for hot-reload
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Development command with hot-reload
# Using polling for file changes in Docker environment
CMD ["npm", "start"]

# Build stage for production build
FROM base AS builder

# Copy package files
COPY src/react-frontend/package*.json ./

# Install production dependencies with legacy peer deps to handle TypeScript conflict
RUN npm ci --legacy-peer-deps

# Copy application code
COPY src/react-frontend/ ./

# Build the React application
RUN npm run build

# Production stage (nginx)
FROM nginx:alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Copy custom nginx configuration
COPY docker/nginx.prod.conf /etc/nginx/conf.d/default.conf

# Copy built React app from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown appuser:appuser /var/run/nginx.pid

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]