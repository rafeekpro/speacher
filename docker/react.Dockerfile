# Multi-stage build for production React frontend
# Stage 1: Build the React application
FROM node:18-alpine AS builder

# Security: Run as non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S reactjs -u 1001 -G nodejs

# Set working directory
WORKDIR /app

# Install dependencies for better caching
COPY src/react-frontend/package*.json ./
RUN npm ci --only=production --legacy-peer-deps && \
    npm cache clean --force

# Install dev dependencies for build
COPY src/react-frontend/package*.json ./
RUN npm ci --legacy-peer-deps

# Copy source code
COPY src/react-frontend/ ./

# Change ownership to non-root user
RUN chown -R reactjs:nodejs /app
USER reactjs

# Build the application with optimizations
ENV NODE_ENV=production
ENV GENERATE_SOURCEMAP=false
ENV INLINE_RUNTIME_CHUNK=false
RUN npm run build

# Stage 2: Production nginx server
FROM nginx:1.25-alpine

# Security: Create non-root user for nginx
RUN addgroup -g 1001 -S nginx-custom && \
    adduser -S nginx-user -u 1001 -G nginx-custom && \
    # Create directories with proper permissions
    mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp \
             /var/log/nginx \
             /var/run/nginx \
             /etc/nginx/conf.d && \
    # Set ownership for nginx directories
    chown -R nginx-user:nginx-custom /var/cache/nginx \
                                     /var/log/nginx \
                                     /var/run/nginx \
                                     /etc/nginx \
                                     /usr/share/nginx/html

# Copy nginx server configuration to conf.d directory
# Use simple config for local development (no backend proxy)
COPY docker/nginx.simple.conf /etc/nginx/conf.d/default.conf

# Fix nginx PID path for non-root user - remove pid directive completely
RUN grep -v '^[[:space:]]*pid[[:space:]]*\/var\/run\/nginx\.pid;[[:space:]]*$' /etc/nginx/nginx.conf > /tmp/nginx.conf && mv /tmp/nginx.conf /etc/nginx/nginx.conf

# Copy built files from builder stage
COPY --from=builder --chown=nginx-user:nginx-custom /app/build /usr/share/nginx/html

# Switch to non-root user
USER nginx-user

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Use non-privileged port
EXPOSE 8080

# Start nginx with custom configuration and writable PID file location
CMD ["nginx", "-g", "daemon off; pid /tmp/nginx.pid;"]