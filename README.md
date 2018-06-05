# Errbot Rocket.Chat
[Errbot](http://errbot.io/) backend for [Rocket.Chat](https://rocket.chat/).

The backend logs in as a Rocket.Chat user, receiving and sending messages.

Tested working with:
- Rocket.Chat 0.65.1
- Errbot 5.2
- Python 3.5

## Table of Contents
- [Set up Rocket.Chat server](#set-up-rocketchat-server)
  - [Create docker-compose.yml file](#create-docker-composeyml-file)
  - [Start Rocket.Chat server](#start-rocketchat-server)
  - [Create Rocket.Chat user](#create-rocketchat-user)
- [Set up AoikRocketChatErrbot](#set-up-aoikrocketchaterrbot)
  - [Clone this repository to local](#clone-this-repository-to-local)
  - [Install AoikRocketChatErrbot](#install-aoikrocketchaterrbot)
  - [Tweak Errbot config module](#tweak-errbot-config-module)
  - [Start Errbot](#start-errbot)
  - [systemd file](#systemd-file)

## Set up Rocket.Chat server
- [Create docker-compose.yml file](#create-docker-composeyml-file)
- [Start Rocket.Chat server](#start-rocketchat-server)
- [Create Rocket.Chat user](#create-rocketchat-user)

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
- [Clone this repository to local](#clone-this-repository-to-local)
- [Install AoikRocketChatErrbot](#install-aoikrocketchaterrbot)
- [Tweak Errbot config module](#tweak-errbot-config-module)
- [Start Errbot](#start-errbot)
- [systemd file](#systemd-file)

### Clone this repository to local
Run:
```
git clone https://github.com/cardoso/errbot-rocketchat
```

### Install AoikRocketChatErrbot
Run:
```
cd errbot-rocketchat

virtualenv venv

venv/bin/python setup.py install
```

This will install AoikRocketChatErrbot's dependency packages, including Errbot.

### Tweak Errbot config module
The Errbot config module is located at
[AoikRocketChatErrbot/src/aoikrocketchaterrbot/config.py](/src/aoikrocketchaterrbot/config.py).

Tweak config values under AOIKROCKETCHATERRBOT_CONFIG:
- BOT_ADMINS (no @ prefix)
- SERVER_URI
- LOGIN_USERNAME
- LOGIN_PASSWORD

### Start Errbot
Run:
```
cd AoikRocketChatErrbot/src/aoikrocketchaterrbot

python -m errbot.cli
```

### systemd file
It is very easy to set up a daemon process for Errbots. For security reasons it should always be runned by a non-sudo user: `sudo useradd -m --user-group errbot-runner`

Create the following systemd file `sudo vim /etc/systemd/system/errbot.service`:
```
[Unit]
Description=Errbot chatbot for Rocket.Chat
After=network.target

[Service]
Environment="LC_ALL=en_US.UTF-8"
ExecStart=/home/errbot-runner/errbot-rocketchat/venv/bin/python -m errbot.cli
Restart=always
RestartSec=10
WorkingDirectory=/home/errbot-runner/errbot-rocketchat/src/aoikrocketchaterrbot
User=errbot-runner
KillSignal=SIGINT

[Install]
WantedBy=multi-user.target
```

Start the daemon and enable it to start at system reboot:
```
sudo systemctl start errbot.service
sudo systemctl enable errbot.service
```
