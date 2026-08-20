# syntax=docker/dockerfile:1
FROM node:20-alpine AS builder

WORKDIR /app

# Instala dependencias
COPY package*.json ./
RUN npm ci

# ARG que recibe la URL pública de la API en tiempo de build
ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}

# Copia el resto del código y compila la app estática
COPY . .
RUN npm run build

# Servidor ligero para el contenido estático
FROM nginx:alpine

# Copia los assets compilados
COPY --from=builder /app/dist /usr/share/nginx/html

# Añade un marcador de build al HTML para invalidar cachés de edge/CDN
RUN sed -i "s|<head>|<head>\\n    <meta name=\"build-time\" content=\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\">|" /usr/share/nginx/html/index.html

# Configuración para SPA: redirige 404 a index.html.
# index.html nunca se cachea (edge debe revalidar), los assets hashados se cachean 1 año.
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    location / { \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
    location = /index.html { \
        add_header Cache-Control "no-cache, no-store, must-revalidate"; \
        add_header Pragma "no-cache"; \
        add_header Expires "0"; \
    } \
    location /assets/ { \
        add_header Cache-Control "public, max-age=31536000, immutable"; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
