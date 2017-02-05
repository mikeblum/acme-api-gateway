## ACME API Gateway

![image](https://raw.githubusercontent.com/mikeblum/acme-api-gateway/master/images/le-logo-standard.png) ![image](https://raw.githubusercontent.com/mikeblum/acme-api-gateway/master/images/aws-api-gateway.png)

Hook for the execellent [Dehydrated](https://github.com/lukas2511/dehydrated) (previously known as letsencrypt.sh).

This hook uses Route 53 to get certificates for securing an Amazon API Gateway. This allows for secure and custom domains for your API.

I wrote a blog post on how to use `acme-api-gateway`: [Acme API Gateway](https://mblum.me/api-gateway/). It automates the tedious process of provisioning HTTPS certificates for custom domains on Amazon's API Gateway service.

### Clone Dehydrated

    git clone https://github.com/lukas2511/dehydrated.git

### Checkout

    cd dehydrated
    git clone https://github.com/mikeblum/acme-api-gateway.git

### Setup

cd into acme-api-gateway:

	cd acme-api-gateway

Add the AWS keys so we can update the Route53 DNS records for this domain.

    vi .env

```bash
#!/bin/bash

export AWS_ACCESS_KEY=########################
export AWS_SECRET_ACCESS_KEY=#################
```

    source ./env

Create a virtualenv:

	virtualenv env
	source ./env/bin/activate

Install dependencies

    pip install -r requirements.txt

* tldextract
* boto3
* route53

### Get Certificates

    ./dehydrated --cron --force --domain {{ domain }} --hook acme-api-gateway/hooks/hook.py --challenge dns-01
    
This will automatically verify and deploy your custom domain and make it available in API Gateway.

Output looks like this:

```
Processing {{ your domain }}
 + Checking domain name(s) of existing cert... unchanged.
 + Checking expire date of existing cert...
 + Valid till Feb 11 20:48:00 2017 GMT (Longer than 30 days). Ignoring because renew was forced!
 + Signing domains...
 + Generating private key...
 + Generating signing request...
 + Requesting challenge for {{ your domain }}...
deploy_challenge
{{ your domain }}
IQYeRiF-3MIymB_PwFHIXAhPPicaiks6ec1uHgdi-aE
removing DNS challenge
creating TXT record for letsencrypt challenge
modified: True
 + Responding to challenge for {{ your domain }}...
clean_challenge
{{ your domain }}
IQYeRiF-3MIymB_PwFHIXAhPPicaiks6ec1uHgdi-aE
removing DNS challenge
removing old TXT record for letsencrypt challenge
{'request_status': 'PENDING', 'request_submitted_at': datetime.datetime(2016, 11, 13, 21, 57, 31, 594000, tzinfo=<UTC>), 'request_id': <built-in function id>}
 + Challenge is valid!
 + Requesting certificate...
 + Checking certificate...
 + Done!
 + Creating fullchain.pem...
deploy_cert
deploying certificates to API Gateway
renewing domain name ({{ your domain }}) in API Gateway
Create Alias record from {{ your domain }} to dqux49yhycipr.cloudfront.net
 + Done!
