## ACME API Gateway

Hook for the excellent [Dehydrated](https://github.com/lukas2511/dehydrated) (previously known as letsencrypt.sh).

This hook uses Route 53 to get certificates for securing an Amazon API Gateway. This allows for secure and custom domains for your API.

### Clone Dehydrated

    git clone https://github.com/lukas2511/dehydrated.git

### Checkout

    cd dehydrated
    git clone https://github.com/mikeblum/acme-api-gateway.git

### Get Certificates

    ./dehydrated --cron --force --domain {{ domain }} --hook acme-api-gateway/hooks/hook.py --challenge dns-01
