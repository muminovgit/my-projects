FROM node:22-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY tsconfig.json ./
COPY src ./src
ENV DATA_DIR=/data
VOLUME /data
CMD ["npm", "start"]
