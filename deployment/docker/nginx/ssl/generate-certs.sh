#!/bin/bash
# Generate self-signed SSL certificate for DataPrime Assistant
# For production use, replace with Let's Encrypt certificates

set -euo pipefail

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_FILE="${CERT_DIR}/dataprime.crt"
KEY_FILE="${CERT_DIR}/dataprime.key"

echo "🔒 Generating self-signed SSL certificate..."

# Generate 2048-bit RSA key and self-signed certificate valid for 365 days
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${KEY_FILE}" \
    -out "${CERT_FILE}" \
    -subj "/C=US/ST=State/L=City/O=Coralogix/OU=Demo/CN=dataprime-demo" \
    -addext "subjectAltName=DNS:dataprime-demo,DNS:localhost,IP:127.0.0.1"

# Set proper permissions
chmod 600 "${KEY_FILE}"
chmod 644 "${CERT_FILE}"

echo "✅ SSL certificate generated successfully!"
echo "   Certificate: ${CERT_FILE}"
echo "   Private Key: ${KEY_FILE}"
echo ""
echo "⚠️  WARNING: This is a self-signed certificate for DEMO purposes only!"
echo "   Browsers will show security warnings."
echo "   For production, use Let's Encrypt:"
echo "   https://letsencrypt.org/getting-started/"
echo ""
echo "📝 Let's Encrypt example (for production):"
echo "   certbot certonly --standalone -d your-domain.com"
echo "   Then update nginx configuration to use:"
echo "   ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;"
echo "   ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;"

