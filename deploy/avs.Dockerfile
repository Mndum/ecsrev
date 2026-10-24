FROM golang:1.24-bookworm AS build
WORKDIR /src
COPY services/AssetValidationServiceV2/go.mod services/AssetValidationServiceV2/go.sum ./
RUN go mod download
COPY services/AssetValidationServiceV2 ./
RUN CGO_ENABLED=0 go build -o /out/avs .

FROM gcr.io/distroless/static-debian12
COPY --from=build /out/avs /avs
EXPOSE 4300
ENTRYPOINT ["/avs"]
