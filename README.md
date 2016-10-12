## ACME API Gateway

![image](https://raw.githubusercontent.com/mikeblum/acme-api-gateway/master/images/le-logo-standard.png =200x) ![image](https://raw.githubusercontent.com/mikeblum/acme-api-gateway/master/images/aws-api-gateway.png =125x)

Hook for the execellent [Dehydrated](https://github.com/lukas2511/dehydrated) (previously known as letsencrypt.sh).

This hook uses Route 53 to get certificates for securing an Amazon API Gateway. This allows for secure and custom domains for your API.

### Clone Dehydrated

    git clone https://github.com/lukas2511/dehydrated.git

### Checkout

    cd dehydrated
    git clone https://github.com/mikeblum/acme-api-gateway.git

### Get Certificates

    ./dehydrated --cron --force --domain {{ domain }} --hook acme-api-gateway/hooks/hook.py --challenge dns-01
    
This will automatically verify and deploy your custom domain and make it available in API Gateway.
