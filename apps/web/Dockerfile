FROM node:24-alpine AS build
WORKDIR /app

COPY package.json tsconfig.json index.html vite.config.ts ./
COPY src ./src
RUN npm install --no-audit --no-fund \
    && npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html
RUN mkdir -p /tmp/nginx/client_temp /tmp/nginx/proxy_temp /tmp/nginx/fastcgi_temp \
    /tmp/nginx/uwsgi_temp /tmp/nginx/scgi_temp \
    && chown -R nginx:nginx /tmp/nginx /usr/share/nginx/html

USER nginx
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
