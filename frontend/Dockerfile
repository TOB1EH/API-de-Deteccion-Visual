# Etapa 1: build de la aplicacion Vue
FROM node:18-alpine AS build

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia solo los archivos de dependencias primero para cachear la capa de npm install
COPY package.json package-lock.json ./

# Instala las dependencias de produccion
RUN npm ci

# Copia el resto del codigo fuente
COPY . .

# Compila la aplicacion para produccion, genera los archivos estaticos en dist/
RUN npm run build

# Etapa 2: servidor Nginx para servir los archivos estaticos
FROM nginx:alpine

# Copia los archivos compilados desde la etapa anterior
COPY --from=build /app/dist /usr/share/nginx/html

# Copia la configuracion personalizada de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expone el puerto 80 para el trafico HTTP
EXPOSE 80

# Nginx se ejecuta en primer plano (PID 1)
CMD ["nginx", "-g", "daemon off;"]
