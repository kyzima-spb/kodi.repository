#!/usr/bin/env sh

CN=${REPO_BASE_URL:-localhost}

privateKey="/etc/ssl/private/nginx.key"
certFile="/etc/ssl/certs/nginx.crt"

mkdir -p "$(dirname $privateKey)" "$(dirname $certFile)"

if [ ! -f "$privateKey" ] || [ ! -f "$certFile" ]; then
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$privateKey" \
    -out "$certFile" \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=${CN}"

  cp "$certFile" /usr/local/share/ca-certificates/
  update-ca-certificates
fi
