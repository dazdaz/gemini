#!/bin/sh
set -e

# Replace the placeholder with the actual backend URL
sed -i "s|__BACKEND_URL__|$BACKEND_URL|g" /usr/share/nginx/html/src/utils/config.js

# Start nginx
nginx -g 'daemon off;'