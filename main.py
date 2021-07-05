from __future__ import absolute_import, division, print_function
import sys
from typing import Optional

 #2017  pip3 install pycliarr==1.0.14
 #2018  pip3 install trakt.py

from trakt import Trakt
from pycliarr.api import RadarrCli
import schedule
import time

from threading import Condition
import logging
import os
import json
from datetime import datetime, timedelta

logging.basicConfig(level=logging.ERROR)

config = {}

class radarrMovs(object):
    def __init__(self, radarrCli):
      self._radarrMovs = None
      self.radarrCli = radarrCli
      self.movs = self.radarrCli.get_movie()
    
    @property
    def movs(self):
        return self._radarrMovs
    
    @movs.setter
    def movs(self, val):
        self._radarrMovs = val
    
    def getImdb(self, imdbId: str):
        for mov in self._radarrMovs:
            if mov.imdbId == imdbId:
                return mov

        return None

    def delete(self, imdbId: str):
        mov = self.getImdb(imdbId=imdbId)
        if not mov:
            return
        self.radarrCli.delete_movie(mov.id, delete_files = True, add_exclusion = True)
        return

class Application(object):
    def __init__(self):
        self.is_authenticating = Condition()

        self.authorization = None
        
        # Bind trakt events
        Trakt.on('oauth.token_refreshed', self.on_token_refreshed)

    def authenticate(self):
        if not self.is_authenticating.acquire(blocking=False):
            print('Authentication has already been started')
            return False

        # Request new device code
        code = Trakt['oauth/device'].code()

        print('Enter the code "%s" at %s to authenticate your account' % (
            code.get('user_code'),
            code.get('verification_url')
        ))

        # Construct device authentication poller
        poller = Trakt['oauth/device'].poll(**code)\
            .on('aborted', self.on_aborted)\
            .on('authenticated', self.on_authenticated)\
            .on('expired', self.on_expired)\
            .on('poll', self.on_poll)

        # Start polling for authentication token
        poller.start(daemon=False)

        # Wait for authentication to complete
        return self.is_authenticating.wait()

    def run(self):
        if not self.authorization:
          self.authenticate()

        if not self.authorization:
            print('ERROR: Authentication required')
            exit(1)
     
        #STrakt.configuration.oauth.from_response(self.authorization)   
        Trakt.configuration.defaults.oauth.from_response(self.authorization)
        
        moviesToDelete = []

        self.radarrMovs = radarrMovs(RadarrCli(config["radarr"]["url"], config["radarr"]["api_key"]))
        
        #Movies seen
        for item in Trakt['sync/history'].get(media='movies', 
                end_at=datetime.now() - timedelta(days=config["days_old"])):
            print(' - %-120s (watched_at: %r)' % (
                 item.title + " (" + str(item.year) + ")",
                 item.watched_at.strftime('%Y-%m-%d %H:%M:%S')
            ))
            #Delete from the Trakt List
            moviesToDelete.append({
                                "ids": {
                                    item.pk[0]:  item.pk[1]
                                }
                            }) 
            #Delete from Radarr
            mov = self.radarrMovs.getImdb(item.pk[1])
            if mov:
              self.radarrMovs.delete(item.pk[1])
              print("deleted from radarr: {}".format(mov))
            else:
              print("... no se encuentra en radarr")
        
    
        #https://github.com/fuzeman/trakt.py/blob/master/trakt/interfaces/users/lists/list_.py
        print("Delete {} movies from the trakt list {} if they exists".format(len(moviesToDelete), config["trakt"]["list"]))
        result= Trakt['users/curif/lists/{}'.format(config["trakt"]["list"])].remove(
                {
                    "movies": moviesToDelete
                }
            )
        print("movies borradas: {}".format(result["deleted"]["movies"]))


    def on_aborted(self):
        """Device authentication aborted.

        Triggered when device authentication was aborted (either with `DeviceOAuthPoller.stop()`
        or via the "poll" event)
        """

        print('Authentication aborted')

        # Authentication aborted
        self.is_authenticating.acquire()
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

    def on_authenticated(self, authorization):
        """Device authenticated.

        :param authorization: Authentication token details
        :type authorization: dict
        """

        # Acquire condition
        self.is_authenticating.acquire()

        # Store authorization for future calls
        self.authorization = authorization

        print('Authentication successful - authorization: %r' % self.authorization)

        # Authentication complete
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

        self.save_token()

    def on_expired(self):
        """Device authentication expired."""

        print('Authentication expired')

        # Authentication expired
        self.is_authenticating.acquire()
        self.is_authenticating.notify_all()
        self.is_authenticating.release()

    def on_poll(self, callback):
        """Device authentication poll.

        :param callback: Call with `True` to continue polling, or `False` to abort polling
        :type callback: func
        """

        # Continue polling
        callback(True)

    def on_token_refreshed(self, authorization):
        # OAuth token refreshed, store authorization for future calls
        self.authorization = authorization

        print('Token refreshed - authorization: %r' % self.authorization)
        self.save_token()

    def save_token(self):
        with open("authtoken.json", 'w') as outfile:
          json.dump(self.authorization, outfile)

def execute():
    app = Application()
    if os.path.exists("authtoken.json"):
        #authorization = os.environ.get('AUTHORIZATION')
        with open("authtoken.json", 'r') as file:
            app.authorization = json.load(file)
    app.run()

if __name__ == '__main__':
    #global config

    # Configure
    if not os.path.exists("config.json"):
        raise Exception("Error config.json not found")
    
    with open("config.json", 'r') as file:
        config  = json.load(file)
        print(config)

    Trakt.base_url = config["trakt"]["base_url"]

    Trakt.configuration.defaults.client(
      id=config["trakt"]["id"],
      secret=config["trakt"]["secret"],
    )

    schedule.every(config["schedule_hours"]).hours.do(execute)
    while True:
        schedule.run_pending()
        print("waiting...")
        time.sleep(60)    

