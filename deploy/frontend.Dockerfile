# Builds the Next.js frontend (served through the .NET website, which proxies to it on localhost:3000).
FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY services/2016-roblox-main/package*.json ./
RUN npm install --no-audit --no-fund
COPY services/2016-roblox-main ./
# next.config.js needs a config.json at build time; the real one is generated at container start.
RUN node ./util/create_config.js && npm run build

FROM node:22-bookworm-slim
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build /app ./
COPY deploy/frontend-entrypoint.js /usr/local/bin/frontend-entrypoint.js
EXPOSE 3000
CMD ["node", "/usr/local/bin/frontend-entrypoint.js"]
