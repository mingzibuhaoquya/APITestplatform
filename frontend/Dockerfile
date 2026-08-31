FROM node:22-alpine AS build
WORKDIR /app

ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN npm config set registry ${NPM_REGISTRY} \
    && npm install -g pnpm@11.19.0 --registry=${NPM_REGISTRY} \
    && pnpm config set registry ${NPM_REGISTRY}

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
