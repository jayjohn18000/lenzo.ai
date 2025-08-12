# Node LTS for Next.js
FROM node:18-alpine

WORKDIR /usr/src/app

# Install deps first for caching
COPY package*.json ./
RUN npm ci

# Copy app
COPY . .

EXPOSE 3000
