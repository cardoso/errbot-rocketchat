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
- [Set up RocketChatErrbot](#set-up-rocketchaterrbot)
  - [Clone this repository to local](#clone-this-repository-to-local)
  - [Install RocketChatErrbot](#install-rocketchaterrbot)
  - [Tweak Errbot config module](#tweak-errbot-config-module)
  - [Start Errbot](#start-errbot)
  - [systemd file](#systemd-file)
  - [using docker](#Docker)
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

Create a new user. The default config in rocketchat uses username
`errbot` and password `errbot`.

## Set up RocketChatErrbot
- [Clone this repository to local](#clone-this-repository-to-local)
- [Install RocketChatErrbot](#install-rocketchaterrbot)
- [Tweak Errbot config module](#tweak-errbot-config-module)
- [Start Errbot](#start-errbot)
- [systemd file](#systemd-file)

### Clone this repository to local
Run:
```
git clone https://github.com/cardoso/errbot-rocketchat
```

### Install RocketChatErrbot
Run:
```
cd errbot-rocketchat

virtualenv venv

venv/bin/python setup.py install
```

This will install RocketChatErrbot's dependency packages, including Errbot.

### Tweak Errbot config module
The Errbot config module is located at
[errbot-rocketchat/src/rocketchat/config.py](/src/rocketchat/config.py).

Tweak config values under ROCKETCHAT_CONFIG:
- BOT_ADMINS (no @ prefix)
- SERVER_URI
- LOGIN_USERNAME
- LOGIN_PASSWORD

### Start Errbot
Run:
```
cd errbot-rocketchat/src/rocketchat

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
WorkingDirectory=/home/errbot-runner/errbot-rocketchat/src/rocketchat
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

### Docker 

 To use the Dockerfile you simply need to create  a config file in the root of the project with the config you wish to load. 
 then inside the source directory ``` docker build -t rocketchaterrbot . && 
 docker run rocketchaterrbot ```
