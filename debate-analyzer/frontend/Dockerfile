FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Use a simple server to serve the static files or just keep it as is for dev
# For now, keeping it as a build image for production-readiness
FROM node:20-alpine
WORKDIR /app
COPY --from=build /app ./
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]
