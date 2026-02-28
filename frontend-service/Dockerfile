# ── PK Finance Frontend (nginx) ──
# Lightweight static file server — ~5 MB RAM

FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static files
COPY static/ /usr/share/nginx/html/

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
