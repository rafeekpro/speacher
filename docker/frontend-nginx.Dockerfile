# Simple nginx container for pre-built React frontend
# This Dockerfile expects the React app to be already built
# It just packages the built files in an nginx container

FROM nginx:alpine

# Copy nginx configuration if it exists
COPY docker/nginx.prod.conf /etc/nginx/conf.d/default.conf

# Copy pre-built frontend files
# The build should be done in the CI/CD pipeline before this step
COPY src/react-frontend/build /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]