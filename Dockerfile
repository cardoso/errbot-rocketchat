FROM python:3.6.5-alpine3.7

RUN apk update && apk upgrade && \
    apk add --no-cache bash git openssh libffi-dev libffi pkgconf gcc g++ openssl openssl-dev


Run  git clone https://github.com/cardoso/errbot-rocketchat
WORKDIR errbot-rocketchat

Run python setup.py install
