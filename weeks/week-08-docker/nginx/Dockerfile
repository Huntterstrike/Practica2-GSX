
# Copy custom Nginx configuration (mirrors Assignment 1 Week 2 setup)
COPY default.conf /etc/nginx/conf.d/default.conf

# Healthcheck: verifies Nginx is actually responding, not just running
# Equivalent to the observability checks we did with systemctl in Assignment 1
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost/ || exit 1

EXPOSE 80
