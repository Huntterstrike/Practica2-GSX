FROM nginx:latest

COPY default.conf /etc/nginx/conf.d/default.conf

# Fix permissions for non-root nginx user
RUN chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    touch /run/nginx.pid && \
    chown nginx:nginx /run/nginx.pid

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost/ || exit 1

USER nginx

EXPOSE 80