# trakt-list-maintain-radarr

This program combines Radarr with Trakt to remove seen movies from your storage.

My working pipeline start identifing a movie (for example seeing a trailer in youtube) and adding the movie to a Trakt list. Later mi Radarr installation detect the movie and download it because I configure Radarr to see that list in Trakt. All is (almost) fully automated, but I want to remove the movie
from the Radarr storage and from the Trakt list after I saw it. This script accomplish those tasks.

# requeriments

Please read the `requirements.txt` to understand the dependencies.

In particular, the `trakt.py` library needs to connect this application to Trakt, and to give permissions to your Trakt user. For that you will need to create a new application in Trakt to obtain your `id` and `secret`.

Goto https://trakt.tv/oauth/applications/new

# config.json

Create a json file (you can copy the `config.json.example`) to the `config/` subdir.

```json
{
    "days_old": 15,
    "schedule_hours": 12,
    "trakt": {
        "base_url": "https://api.trakt.tv",
        "id": "xxx",
        "secret": "xxx",
        "list": "xx"
    },
    "radarr": {
        "url": "http://192.168.0.10:7878", 
        "api_key": "xxx"
    }
}
```

* days_old: how many days a movie remain in disk after you saw it.
* schedule_hours: time between executions
* trakt: url, id, secret, and the name of the list to look for new movies.
* radarr: your radar installation information. The `api_key` is in `settings` -> `general` -> `security`

# first run

The script will get a login token from the Trakt site. For that it will show a confirmation code that you need to fill in the activation page: https://trakt.tv/activate
    
    auth...
    Enter the code "9131XXXX" at https://trakt.tv/activate to authenticate your account

Don´t worries, you have enough time to do it.

After the permission is granted, the program will write a json file with the token in the `config` subdir. When the token expires the script will renew it automatically.

# Docker

A `dockerfile` is provided, you can build the container and run it with docker-compose for example

```yaml
  trakt_maintaint:
    build:
      context: ./trakt-list-maintain-radarr
    image: trakt-list-maintain-radarr:latest
    volumes:
     - /home/xxxx/trakt-list-maintain-radarr/config:/usr/src/app/config
    environment:
      TZ: America/Argentina/Buenos_Aires
    restart: unless-stopped

```
