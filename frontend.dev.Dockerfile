# Development Dockerfile for Next.js (with hot reload)
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY frontend-nextjs/package*.json ./

# Install all dependencies (including dev)
RUN npm install

# Copy source code (will be overridden by volume mount in dev)
COPY frontend-nextjs/ .

# Expose port
EXPOSE 3000

# Development server
CMD ["npm", "run", "dev"]
