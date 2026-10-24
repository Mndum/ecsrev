# Builds the .NET website (also serves the admin panel).
FROM node:20-bookworm AS admin
WORKDIR /src/services/admin
COPY services/admin/package*.json ./
RUN npm install --no-audit --no-fund
COPY services/admin ./
RUN npm run build

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY services/Roblox ./services/Roblox
RUN dotnet publish services/Roblox/Roblox.Website/Roblox.Website.csproj -c Release -o /out -p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:8.0
# The project targets net6.0, which is end-of-life; run it on the current runtime.
ENV DOTNET_ROLL_FORWARD=Major \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    ASPNETCORE_ENVIRONMENT=Production
WORKDIR /app
COPY --from=build /out ./
COPY --from=admin /src/services/admin/public /app-data/admin-public
COPY services/Roblox/Roblox.Libraries/Templates /app-data/templates
COPY services/Roblox/Roblox.Libraries/Json /app-data/json
COPY services/api/public /app-data/public-seed
COPY deploy/web-entrypoint.sh /usr/local/bin/web-entrypoint.sh
RUN chmod +x /usr/local/bin/web-entrypoint.sh && mkdir -p /app-data/economy-chat /data
EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/web-entrypoint.sh"]
