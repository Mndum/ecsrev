# Builds the Next.js frontend (served through the .NET website, which proxies to it on localhost:3000).
FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY services/2016-roblox-main/package*.json ./
RUN npm install --no-audit --no-fund
COPY services/2016-roblox-main ./
# next.config.js needs a config.json at build time. Pages are prerendered during the build with this
# config baked in, so PUBLIC_URL must be applied here too (the entrypoint's runtime rewrite is too late
# for prerendered pages). Changing PUBLIC_URL therefore needs a rebuild, which `ecs.py start` does.
ARG PUBLIC_URL=http://localhost:5000
RUN node ./util/create_config.js && \
    node -e "const fs=require('fs'),u=process.env.PUBLIC_URL.replace(/\/+\$/,''),c=JSON.parse(fs.readFileSync('config.json','utf8'));c.publicRuntimeConfig.backend.baseUrl=u;c.publicRuntimeConfig.backend.apiFormat=u+'/apisite/{0}{1}';fs.writeFileSync('config.json',JSON.stringify(c))" && \
    npm run build

FROM node:22-bookworm-slim
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build /app ./
COPY deploy/frontend-entrypoint.js /usr/local/bin/frontend-entrypoint.js
EXPOSE 3000
CMD ["node", "/usr/local/bin/frontend-entrypoint.js"]
