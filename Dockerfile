FROM golang:1.25-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /homestate ./cmd/homestate/

FROM alpine:3.20
RUN apk add --no-cache ca-certificates tzdata
COPY --from=builder /homestate /usr/local/bin/homestate
COPY config.example.json /etc/homestate/config.json
WORKDIR /data
ENTRYPOINT ["homestate"]
CMD ["-config", "/etc/homestate/config.json"]
