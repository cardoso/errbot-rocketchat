[:var_set('', """
# Compile command
aoikdyndocdsl -s README.src.md -n aoikdyndocdsl.ext.all::nto -g README.md
""")
]\
[:HDLR('heading', 'heading')]\
# AoikRocketChatErrbot
[Errbot](http://errbot.io/) backend for [Rocket.Chat](https://rocket.chat/).

The backend logs in as a Rocket.Chat user, receiving and sending messages.

Tested working with:
- Rocket.Chat 0.48.1
- Errbot 4.3.4
- Python 3.5

## Table of Contents
[:toc(beg='next', indent=-1)]

## Set up Rocket.Chat server
[:tod()]

### Create docker-compose.yml file
Run:
```
cat <<'ZZZ' > docker-compose.yml
version: '2'
services:
  rocket.chat:
    depends_on:
      - db
    image: rocket.chat:0.48.1
    ports:
      - 3000:3000
    volumes_from:
      - db
    environment:
      ROOT_URL: http://127.0.0.1:3000
  db:
    image: mongo:3.4.0
ZZZ
```

### Start Rocket.Chat server
Run:
```
docker-compose up
```

### Create Rocket.Chat user
Open `http://127.0.0.1:3000/` in browser.

Create a new user. The default config in AoikRocketChatErrbot uses username
`errbot` and password `errbot`.

## Set up AoikRocketChatErrbot
[:tod()]

### Clone this repository to local
Run:
```
git clone https://github.com/AoiKuiyuyou/AoikRocketChatErrbot
```

### Install AoikRocketChatErrbot
Run:
```
cd AoikRocketChatErrbot

python setup.py install
```

This will install AoikRocketChatErrbot's dependency packages, including Errbot.

### Tweak Errbot config module
The Errbot config module is located at
[AoikRocketChatErrbot/src/aoikrocketchaterrbot/config.py](/src/aoikrocketchaterrbot/config.py).

Tweak config values under AOIKROCKETCHATERRBOT_CONFIG:
- SERVER_URI
- LOGIN_USERNAME
- LOGIN_PASSWORD

### Start Errbot
Run:
```
cd AoikRocketChatErrbot/src/aoikrocketchaterrbot

python -m errbot.cli
```
