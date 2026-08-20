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

# Configuración mínima para SPA: redirige 404 a index.html
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
