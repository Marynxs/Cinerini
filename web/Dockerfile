# Imagem do front, em dois estágios.
#
# O Vite embute as variáveis `VITE_*` no bundle durante o build — elas não
# existem em tempo de execução. Por isso a URL da API entra como argumento de
# build, e não como variável do contêiner: passá-la no `environment` não teria
# efeito nenhum.
FROM node:22-alpine AS build

WORKDIR /app

# `npm ci` e não `npm install`: instala exatamente o que está no lock, que é
# o ponto de ter o lock versionado.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# O segundo estágio só carrega os estáticos. O Node inteiro fica para trás:
# a imagem final não precisa de compilador para servir HTML.
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
