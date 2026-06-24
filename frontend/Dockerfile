# Build the CRA static bundle, then serve it on $PORT.
# Railway always uses a Dockerfile when present, so this is the deploy path; it
# also works under docker-compose (which maps 3000:80, PORT defaulting to 80).
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --silent
COPY . .
# CRA bakes REACT_APP_* at build time. Railway passes the service variable as a
# build arg; declare it so the API base is compiled into the bundle.
ARG REACT_APP_API_BASE
ENV REACT_APP_API_BASE=$REACT_APP_API_BASE
RUN npm run build

FROM node:18-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/build ./build
ENV PORT=80
EXPOSE 80
# -s = SPA mode (serve index.html for client-side routes)
CMD ["sh", "-c", "serve -s build -l ${PORT:-80}"]
