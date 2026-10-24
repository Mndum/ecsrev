#!/bin/bash
# Renders appsettings.json from environment variables, seeds the data volume, then starts the website.
set -euo pipefail

: "${PUBLIC_URL:?PUBLIC_URL is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${JWT_SECRET:?JWT_SECRET is required}"
# hCaptcha is only used when you provide real keys (HCAPTCHA_SITEKEY / HCAPTCHA_SECRET).
if [ -n "${HCAPTCHA_SITEKEY:-}" ] && [ -n "${HCAPTCHA_SECRET:-}" ]; then CAPTCHA_DISABLED=false; else CAPTCHA_DISABLED=true; fi

DATA=/data
mkdir -p "$DATA/storage/asset" "$DATA/public/images/thumbnails" "$DATA/public/images/groups" "$DATA/public/UnsecuredContent"
# Seed bundled public files (images etc.) without overwriting anything already in the volume.
cp -rn /app-data/public-seed/. "$DATA/public/" 2>/dev/null || true

cat > /app/appsettings.json <<JSON
{
  "Urls": "http://0.0.0.0:5000",
  "Logging": { "LogLevel": { "Default": "Warning", "Microsoft.AspNetCore": "Warning" } },
  "Twitter": { "ApiKey": "unused", "ApiKeySecret": "unused", "Bearer": "unused" },
  "PackageShirtAssetId": -1,
  "PackagePantsAssetId": -1,
  "PackageLeftArmAssetId": -1,
  "PackageRightArmAssetId": -1,
  "PackageLeftLegAssetId": -1,
  "PackageRightLegAssetId": -1,
  "PackageTorsoAssetId": -1,
  "SignupAssetIds": [],
  "SignupAvatarAssetIds": [],
  "CdnBaseUrl": "",
  "BaseUrl": "${PUBLIC_URL}",
  "Authorization": "${INTERNAL_AUTH:-internal-auth}",
  "Postgres": "Host=${POSTGRES_HOST:-db}; Database=${POSTGRES_DB:-ecs}; Password=${POSTGRES_PASSWORD}; Username=${POSTGRES_USER:-ecs}; Maximum Pool Size=20",
  "Redis": "${REDIS_HOST:-redis}",
  "AssetValidation": { "BaseUrl": "http://localhost:4300", "Authorization": "${INTERNAL_AUTH:-internal-auth}" },
  "Render": { "BaseUrl": "ws://localhost:3189", "Authorization": "render-disabled" },
  "GameServerAuthorization": "${INTERNAL_AUTH:-internal-auth}",
  "OwnerUserId": "1",
  "HCaptcha": {
    "Public": "${HCAPTCHA_SITEKEY:-10000000-ffff-ffff-ffff-000000000001}",
    "Private": "${HCAPTCHA_SECRET:-0x0000000000000000000000000000000000000000}",
    "Disabled": "${CAPTCHA_DISABLED}"
  },
  "BotAuthorization": "${INTERNAL_AUTH:-internal-auth}",
  "RccAuthorization": "${INTERNAL_AUTH:-internal-auth}",
  "InfluxDB": { "Website": { "BaseUrl": "", "Authorization": "" } },
  "Directories": {
    "Storage": "$DATA/storage/",
    "Asset": "$DATA/storage/asset/",
    "Public": "$DATA/public/",
    "Thumbnails": "$DATA/public/images/thumbnails/",
    "GroupIcons": "$DATA/public/images/groups/",
    "XmlTemplates": "/app-data/templates/",
    "JsonData": "/app-data/json/",
    "AdminBundle": "/app-data/admin-public/",
    "EconomyChatBundle": "/app-data/economy-chat/"
  },
  "Jwt": { "Sessions": "${JWT_SECRET}" },
  "Bootstrap": { "OwnerPassword": "${OWNER_PASSWORD:-}" },
  "AllowedHosts": "*"
}
JSON

cd /app
exec dotnet Roblox.Website.dll
