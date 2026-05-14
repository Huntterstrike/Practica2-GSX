FROM alpine:3.20 AS builder

WORKDIR /src

COPY default.conf index.html ./

# Validate and stage only the runtime assets that the final image needs.
RUN grep -q "GreenDevCorp Nginx Container" index.html && \
    mkdir -p /out/etc/nginx/conf.d /out/usr/share/nginx/html && \
    cp default.conf /out/etc/nginx/conf.d/default.conf && \
    cp index.html /out/usr/share/nginx/html/index.html

FROM nginx:latest

COPY --from=builder --chown=nginx:nginx /out/etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf
COPY --from=builder --chown=nginx:nginx /out/usr/share/nginx/html/index.html /usr/share/nginx/html/index.html

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
