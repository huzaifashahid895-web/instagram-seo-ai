# frontend/Dockerfile — AI SEO & Social Media Manager (Phase 1)
# Cost classification: FREE + OPEN SOURCE (Node, Vite, React, etc.)

FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev"]
