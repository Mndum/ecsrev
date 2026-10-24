# One-shot job: applies the database migrations.
FROM node:20-bookworm-slim
WORKDIR /api
RUN npm install --no-audit --no-fund knex@0.95 pg
RUN mkdir -p public/images
COPY services/api/knexfile.js ./
COPY services/api/migrations ./migrations
CMD ["sh", "-c", "printf '{\"knex\":{\"client\":\"pg\",\"connection\":{\"host\":\"%s\",\"user\":\"%s\",\"password\":\"%s\",\"database\":\"%s\"}}}' \"${POSTGRES_HOST:-db}\" \"${POSTGRES_USER:-ecs}\" \"$POSTGRES_PASSWORD\" \"${POSTGRES_DB:-ecs}\" > config.json && npx knex migrate:latest"]
