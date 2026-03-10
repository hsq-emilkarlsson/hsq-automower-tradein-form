# syntax=docker/dockerfile:1

ARG NODE_VERSION=24.11.1

# Build stage
FROM node:${NODE_VERSION}-alpine AS builder

WORKDIR /app

COPY package*.json package-lock.json .npmrc ./
RUN npm pkg delete scripts.prepare && \
    npm ci --prefer-offline --no-audit && \
    rm -f .npmrc

COPY tsconfig*.json ./
COPY . .
RUN npm run build

# Production stage
FROM node:${NODE_VERSION}-alpine AS production

RUN apk add --no-cache dumb-init

WORKDIR /app

ENV NODE_ENV=production

COPY package*.json package-lock.json .npmrc ./
RUN npm pkg delete scripts.prepare && \
    npm ci --prefer-offline --no-audit --omit=dev && \
    npm cache clean --force && \
    rm -f .npmrc

COPY --from=builder --chown=node:node /app/dist ./dist

USER node

EXPOSE 4001

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["node", "--enable-source-maps", "dist/main.js"]