FROM python:3.6.5-alpine3.7

RUN apk update && apk upgrade && \
    apk add --no-cache bash git openssh libffi-dev libffi pkgconf gcc g++ openssl openssl-dev shadow

RUN useradd -u 9999 errbot

Run  git clone https://github.com/cardoso/errbot-rocketchat
RUN chown -R errbot  errbot-rocketchat

WORKDIR errbot-rocketchat

Run python setup.py install


WORKDIR /AoikRocketChatErrbot/src/aoikrocketchaterrbot
RUN chown -R errbot  /AoikRocketChatErrbot/src/aoikrocketchaterrbot
COPY ./config.py /AoikRocketChatErrbot/src/aoikrocketchaterrbot/config.py

USER errbot
CMD python -m errbot.cli
