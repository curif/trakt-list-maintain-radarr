from __future__ import absolute_import, division, print_function
import sys
from typing import Optional

 #2017  pip3 install pycliarr==1.0.14
 #2018  pip3 install trakt.py

from trakt import Trakt
from pycliarr.api import RadarrCli

from threading import Condition
import logging
import os
import json
from datetime import datetime, timedelta

logging.basicConfig(level=logging.ERROR)

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
        self.days_old = 15
        
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
     
        self.radarrMovs = radarrMovs(RadarrCli('http://192.168.0.10:7878', '742842f6ea5347acab6791eeb8107b0a'))
        
        mov = self.radarrMovs.getImdb('tt8332802')
        print(mov)
        self.radarrMovs.delete('tt8332802')
        
    
        itemABorrar=None
        for x, item in enumerate(Trakt['users/curif/lists/aBajar'].items(media='movies')):
            print("=========================================================")
            print(' - %-120s' % (
                item.title + " (" + str(item.year) + ")" + str(item.pk),
                ))
            if item.pk == ('imdb', 'tt8332802'):
                itemABorrar = item
            
            # mov=None
            # if item.pk[0] == 'imdb':
            #     mov = radarr_cli.lookup_movie(imdb_id = item.pk[1])
            # elif item.pk[0] == 'tmdb':
            #     mov = radarr_cli.lookup_movie(tmdb_id = item.pk[1])
            # if mov :
            #     print("=======", mov.cleanTitle, mov.path)
            #     print(mov)
                
        
        if itemABorrar:
            #https://github.com/fuzeman/trakt.py/blob/master/trakt/interfaces/users/lists/list_.py
            print("borra item " + str(itemABorrar) + str(itemABorrar.pk))
            result= Trakt['users/curif/lists/aBajar'].remove(
                {
                    "movies": [
                        {
                            "ids": {
                                itemABorrar.pk[0]:  itemABorrar.pk[1]
                            }
                        }
                    ]
                }
            )
            print(result)
            
    #     for item in Trakt['sync/history'].get(media='movies',per_page= 50, end_at=datetime.now() - timedelta(days=self.days_old)):
            
    # #        https://traktpy.readthedocs.io/en/latest/sourcecode/trakt/trakt.objects.movie.html
    #         print(' - %-120s (watched_at: %r)' % (
    #             item.title + " (" + str(item.year) + ")",
    #             item.watched_at.strftime('%Y-%m-%d %H:%M:%S')
    #         ))
    #     for item in Trakt['users'].likes('lists', pagination=True):
    #         print(item)
 


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


if __name__ == '__main__':
    # Configure
    Trakt.base_url = 'https://api.trakt.tv'

    Trakt.configuration.defaults.client(
      id='1f70c35e400a35a1ffa41f9a826401177f4217748e9b52e685df25f992a0f676',
      secret='2429de6de1e07ab94114a8b75e6caf6b261c566bd5f879a3c40b0b8dab777140'
    )
    app = Application()
    if os.path.exists("authtoken.json"):
        #authorization = os.environ.get('AUTHORIZATION')
        with open("authtoken.json", 'r') as file:
            app.authorization = json.load(file)

    app.run()
