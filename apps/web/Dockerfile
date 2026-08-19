FROM node:24-alpine AS build
WORKDIR /app

COPY package.json package-lock.json tsconfig.json index.html vite.config.ts ./
COPY public ./public
COPY src ./src
RUN npm ci --no-audit --no-fund \
    && npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html
RUN chown -R nginx:nginx /usr/share/nginx/html

USER nginx
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
