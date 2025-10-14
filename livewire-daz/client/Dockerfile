FROM nginx:alpine

# Install sed for placeholder replacement
RUN apk add --no-cache sed

# Create the directory structure
RUN mkdir -p /usr/share/nginx/html

# Copy the main application file
COPY index.html /usr/share/nginx/html/index.html

# Copy other required files
COPY styles /usr/share/nginx/html/styles
COPY src /usr/share/nginx/html/src
COPY assets /usr/share/nginx/html/assets

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy and set up the startup script
COPY run.sh /run.sh
RUN chmod +x /run.sh

# Create a simple health check file
RUN echo "OK" > /usr/share/nginx/html/health

# Expose port 8080 (Cloud Run requirement)
EXPOSE 8080

# Start the application
CMD ["/run.sh"]