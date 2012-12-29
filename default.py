# -*- coding: utf-8 -*-
#
#      Copyright (C) 2012 David Gray (N3MIS15)
#      N3MIS15@gmail.com
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt. If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import xbmc
import xbmcgui
import xbmcaddon

import json
import urllib2
import base64
import hashlib

__addon__        = xbmcaddon.Addon(id='script.trakt.sync')
__addonpath__    = __addon__.getAddonInfo('path')
__setting__      = __addon__.getSetting
__getstring__    = __addon__.getLocalizedString

trakt_username = __setting__('trakt_username')
trakt_password = hashlib.sha1(__setting__('trakt_password')).hexdigest()
trakt_apikey   = __setting__('trakt_apikey')


def get_bool(boolean):
    return __setting__(boolean) == 'true'


def xbmc_json(params):
    """ Helper for XBMC JSON communication. """
    data = json.JSONEncoder().encode(params)
    request = xbmc.executeJSONRPC(data)
    response = json.JSONDecoder().decode(request)

    try:
        return response['result']
    except:
        quit(response['error']['message'])


def gui_notification(title, message):
    xbmc_json({"jsonrpc": "2.0", "method": "GUI.ShowNotification", "params": {"title": title, "message": message}, "id": 0})


def trakt_api(url, params={}):
    """ Helper for trakt.tv API communication. """ 

    params = json.JSONEncoder().encode(params)
    request = urllib2.Request(url, params)
    base64string = base64.encodestring('%s:%s' % (trakt_username, trakt_password)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)

    response = urllib2.urlopen(request).read()
    response = json.JSONDecoder().decode(response)

    return response


def xbmc_to_trakt_movie(movie, playcount=False):
    """ Helper to convert XBMC movie into a format trakt can use. """

    trakt_movie = {'title': movie['title'], 'year': movie['year']}

    if movie['imdbnumber'].startswith('tt'):
        trakt_movie['imdb_id'] = movie['imdbnumber']

    elif movie['imdbnumber'].isdigit():
        trakt_movie['tmdb_id'] = movie['imdbnumber']

    if playcount:
        trakt_movie['plays'] = movie['playcount']

    return trakt_movie


def compare_show(xbmc_show, trakt_show):
    missing = []
    trakt_seasons = [x['season'] for x in trakt_show['seasons']]

    for xbmc_episode in xbmc_show['episodes']:
        if xbmc_episode['season'] not in trakt_seasons:
            missing.append(xbmc_episode)
        else:
            for trakt_season in trakt_show['seasons']:
                if xbmc_episode['season'] == trakt_season['season']:
                    if xbmc_episode['episode'] not in trakt_season['episodes']:
                        missing.append(xbmc_episode)

    return missing


def compare_show_watched_trakt(xbmc_show, trakt_show):
    missing = []

    for xbmc_episode in xbmc_show['episodes']:
        if xbmc_episode['playcount']:
            for trakt_season in trakt_show['seasons']:
                if xbmc_episode['season'] == trakt_season['season']:
                    if xbmc_episode['episode'] not in trakt_season['episodes']:
                        missing.append(xbmc_episode)

    return missing


def compare_show_watched_xbmc(xbmc_show, trakt_show):
    missing = []

    for xbmc_episode in xbmc_show['episodes']:
        if not xbmc_episode['playcount']:
            for trakt_season in trakt_show['seasons']:
                if xbmc_episode['season'] == trakt_season['season']:
                    if xbmc_episode['episode'] in trakt_season['episodes']:
                        missing.append(xbmc_episode)

    return missing


class SyncMovies():
    xbmc_movies = []
    trakt_movies = []
    progress = xbmcgui.DialogProgress()


    def MoviesExists(self):
        if not self.xbmc_movies:
            print 'No XBMC movies were found'

        if not self.trakt_movies:
            print 'No trakt movies were found'

        if self.xbmc_movies and self.trakt_movies:
            return True
        else:
            return False


    def GetFromXBMC(self):
        print 'Getting movies from XBMC'
        self.progress.create(__getstring__(1100), line1=__getstring__(1101), line2=' ', line3=' ')
        xbmc.sleep(1000)
        self.xbmc_movies = xbmc_json({"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "imdbnumber", "year", "playcount"]}, "id": 0})['movies']



    def GetFromTrakt(self):
        print 'Getting movies from trakt.tv'
        self.progress.update(10, line1=__getstring__(1102))
        xbmc.sleep(1000)
        self.trakt_movies = trakt_api('http://api.trakt.tv/user/library/movies/all.json/%s/%s' % (trakt_apikey, trakt_username))


    def AddToTrakt(self):
        if self.MoviesExists():
            self.progress.update(30, line1=__getstring__(1106), line2=' ', line3=' ')
            xbmc.sleep(1000)
            print 'Checking for XBMC movies that are not on trakt.tv'

            add_to_trakt = []
            trakt_imdb_ids = [x['imdb_id'] for x in self.trakt_movies if 'imdb_id' in x]
            trakt_tmdb_ids = [x['tmdb_id'] for x in self.trakt_movies if 'tmdb_id' in x]
            trakt_titles = [x['title'] for x in self.trakt_movies if 'title' in x]

            for xbmc_movie in self.xbmc_movies:
                #Compare IMDB IDs
                if xbmc_movie['imdbnumber'].startswith('tt'):
                    if xbmc_movie['imdbnumber'] not in trakt_imdb_ids:
                        add_to_trakt.append(xbmc_movie)

                #Compare TMDB IDs
                elif xbmc_movie['imdbnumber'].isdigit():
                    if xbmc_movie['imdbnumber'] not in trakt_tmdb_ids:
                        add_to_trakt.append(xbmc_movie)

                #Compare titles if unknown ID type
                else:
                    if xbmc_movie['title'] not in trakt_titles:
                        add_to_trakt.append(xbmc_movie)

            if add_to_trakt:
                print '%i movie(s) will be added to trakt.tv collection' % len(add_to_trakt)
                self.progress.update(45, line2='%i %s' % (len(add_to_trakt), __getstring__(1110)))

                url = 'http://api.trakt.tv/movie/library/' + trakt_apikey
                params = {'movies': [xbmc_to_trakt_movie(x) for x in add_to_trakt]}

                trakt_api(url, params)

                self.GetFromTrakt()
                        
            else:
                print 'trakt.tv movie collection is up to date'


    def UpdatePlaysTrakt(self):
        if self.MoviesExists():
            self.progress.update(60, line1=__getstring__(1107), line2=' ', line3=' ')
            xbmc.sleep(1000)
            print 'Checking if trakt.tv playcount is up to date with XBMC'

            update_playcount = []
            trakt_playcounts = {}

            for trakt_movie in self.trakt_movies:
                if 'tmdb_id' in trakt_movie:
                    trakt_playcounts[trakt_movie['tmdb_id']] = trakt_movie['plays']

                if 'imdb_id' in trakt_movie:
                    trakt_playcounts[trakt_movie['imdb_id']] = trakt_movie['plays']

                trakt_playcounts[trakt_movie['title']] = trakt_movie['plays']


            for xbmc_movie in self.xbmc_movies:
                if xbmc_movie['imdbnumber'] in trakt_playcounts:
                    if trakt_playcounts[xbmc_movie['imdbnumber']] < xbmc_movie['playcount']:
                        update_playcount.append(xbmc_movie)

                elif xbmc_movie['title'] in trakt_playcounts:
                    if trakt_playcounts[xbmc_movie['title']] < xbmc_movie['playcount']:
                        update_playcount.append(xbmc_movie)

                else:
                    print 'Could not match %s (%i)' % (xbmc_movie['title'].encode('utf-8'), xbmc_movie['year'])


            if update_playcount:
                print '%i movie(s) playcount will be updated on trakt.tv' % len(update_playcount)
                self.progress.update(75, line2='%i %s' % (len(update_playcount), __getstring__(1112)))

                # Send request to update playcounts on trakt.tv
                url = 'http://api.trakt.tv/movie/seen/' + trakt_apikey
                params = {'movies': [xbmc_to_trakt_movie(x, playcount=True) for x in update_playcount]}

                trakt_api(url, params)

            else:
                print 'trakt.tv movie playcount is up to date'


    def UpdatePlaysXBMC(self):
        if self.MoviesExists():
            self.progress.update(85, line1=__getstring__(1108), line2=' ', line3=' ')
            xbmc.sleep(1000)
            print 'Checking if trakt.tv playcount is up to date with XBMC'

            update_playcount = []
            trakt_playcounts = {}

            for trakt_movie in self.trakt_movies:
                if 'tmdb_id' in trakt_movie:
                    trakt_playcounts[trakt_movie['tmdb_id']] = trakt_movie['plays']

                if 'imdb_id' in trakt_movie:
                    trakt_playcounts[trakt_movie['imdb_id']] = trakt_movie['plays']

                trakt_playcounts[trakt_movie['title']] = trakt_movie['plays']

            for xbmc_movie in self.xbmc_movies:
                if xbmc_movie['imdbnumber'] in trakt_playcounts:
                    if trakt_playcounts[xbmc_movie['imdbnumber']] > xbmc_movie['playcount']:
                        xbmc_movie['playcount'] = trakt_playcounts[xbmc_movie['imdbnumber']]
                        update_playcount.append(xbmc_movie)

                elif xbmc_movie['title'] in trakt_playcounts:
                    if trakt_playcounts[xbmc_movie['title']] > xbmc_movie['playcount']:
                        xbmc_movie['playcount'] = trakt_playcounts[xbmc_movie['title']]
                        update_playcount.append(xbmc_movie)

                else:
                    print 'Could not match %s (%i)' % (xbmc_movie['title'].encode('utf-8'), xbmc_movie['year'])


            if update_playcount:
                print '%i movie(s) playcount will be updated on XBMC' % len(update_playcount)
                self.progress.update(90, line2='%i %s' % (len(update_playcount), __getstring__(1113)))

                for movie in update_playcount:
                    xbmc_json({"jsonrpc": "2.0", "method": "VideoLibrary.SetMovieDetails", "params": {"movieid": movie['movieid'], "playcount": movie['playcount']}, "id": 0})

            else:
                print 'XBMC movie playcount is up to date'


    def Run(self):
        self.GetFromXBMC()
        self.GetFromTrakt()

        if get_bool('add_movies_to_trakt'):
            self.AddToTrakt()

        if get_bool('trakt_movie_playcount'):
            self.UpdatePlaysTrakt()

        if get_bool('xbmc_movie_playcount'):
            self.UpdatePlaysXBMC()

        self.progress.update(100, line1=__getstring__(1109), line2=' ', line3=' ')
        xbmc.sleep(1000)

        self.progress.close()


class SyncEpisodes():
    xbmc_shows = []
    trakt_shows = {'collection': [], 'watched': []}
    progress = xbmcgui.DialogProgress()


    def ShowsExists(self, type):
        if not self.xbmc_shows:
            print 'No XBMC shows were found'

        if not self.trakt_shows[type]:
            print 'No trakt shows were found'

        if self.xbmc_shows and self.trakt_shows[type]:
            return True
        else:
            return False


    def GetFromXBMC(self):
        print 'Getting episodes from XBMC'
        self.progress.create(__getstring__(1103), line1=__getstring__(1104), line2=' ', line3=' ')
        xbmc.sleep(1000)
        shows = xbmc_json({"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "imdbnumber"]}, "id": 0})['tvshows']

        self.progress.update(5, line1=__getstring__(1104))
        for show in shows:
            show['episodes'] = []

            episodes = xbmc_json({"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"tvshowid": show['tvshowid'], "properties": ["season", "episode", "playcount"]}, "id": 0})
            if 'episodes' in episodes:
                episodes = episodes['episodes']

                show['episodes'] = [x for x in episodes if type(x) == type(dict())]

        self.xbmc_shows = [x for x in shows if x['episodes']]


    def GetCollectionFromTrakt(self):
        print 'Getting episode collection from trakt.tv'
        self.progress.update(10, line1=__getstring__(1105), line2=' ', line3=' ')
        xbmc.sleep(1000)
        self.trakt_shows['collection'] = trakt_api('http://api.trakt.tv/user/library/shows/collection.json/%s/%s' % (trakt_apikey, trakt_username))


    def AddToTrakt(self):
        if self.ShowsExists('collection'):
            self.progress.update(30, line1=__getstring__(1106))
            xbmc.sleep(1000)
            print 'Checking for XBMC episodes that are not on trakt.tv'

            add_to_trakt = []
            trakt_imdb_index = {}
            trakt_tvdb_index = {}
            trakt_title_index = {}

            for i in range(len(self.trakt_shows['collection'])):
                if 'imdb_id' in self.trakt_shows['collection'][i]:
                    trakt_imdb_index[self.trakt_shows['collection'][i]['imdb_id']] = i

                if 'tvdb_id' in self.trakt_shows['collection'][i]:
                    trakt_tvdb_index[self.trakt_shows['collection'][i]['tvdb_id']] = i

                trakt_title_index[self.trakt_shows['collection'][i]['title']] = i

            for xbmc_show in self.xbmc_shows:
                missing = []

                #IMDB ID
                if xbmc_show['imdbnumber'].startswith('tt'):
                    if xbmc_show['imdbnumber'] not in trakt_imdb_index.keys():
                        missing = xbmc_show['episodes']

                    else:
                        trakt_show = self.trakt_shows['collection'][trakt_imdb_index[xbmc_show['imdbnumber']]]
                        missing = compare_show(xbmc_show, trakt_show)

                #TVDB ID
                elif xbmc_show['imdbnumber'].isdigit():
                    if xbmc_show['imdbnumber'] not in trakt_tvdb_index.keys():
                        missing = xbmc_show['episodes']

                    else:
                        trakt_show = self.trakt_shows['collection'][trakt_tvdb_index[xbmc_show['imdbnumber']]]
                        missing = compare_show(xbmc_show, trakt_show)

                #Title
                else:
                    if xbmc_show['title'] not in trakt_title_index.keys():
                        missing = xbmc_show['episodes']

                    else:
                        trakt_show = self.trakt_shows['collection'][trakt_title_index[xbmc_show['title']]]
                        missing = compare_show(xbmc_show, trakt_show)

                if missing:
                    show = {'title': xbmc_show['title'], 'episodes': [{'episode': x['episode'], 'season': x['season']} for x in missing]}
                    
                    if xbmc_show['imdbnumber'].isdigit():
                        show['tvdb_id'] = xbmc_show['imdbnumber']
                    else:
                        show['imdb_id'] = xbmc_show['imdbnumber']

                    add_to_trakt.append(show)

            if add_to_trakt:
                print '%i shows(s) shows are missing episodes on trakt.tv' % len(add_to_trakt)
                self.progress.update(35, line1=__getstring__(1106), line2='%i %s' % (len(add_to_trakt), __getstring__(1111)))
                xbmc.sleep(1000)

                for show in add_to_trakt:
                    self.progress.update(50, line1=__getstring__(1106), line2=show['title'], line3='%i %s' % (len(show['episodes']), __getstring__(1114)))
                    trakt_api('http://api.trakt.tv/show/episode/library/'+trakt_apikey, show)

            else:
                print 'trakt.tv episode collection is up to date'


    def GetWatchedFromTrakt(self):
        print 'Getting watched episodes from trakt.tv'
        self.progress.update(60, line1=__getstring__(1105), line2=' ', line3=' ')
        xbmc.sleep(1000)
        self.trakt_shows['watched'] = trakt_api('http://api.trakt.tv/user/library/shows/watched.json/%s/%s' % (trakt_apikey, trakt_username))


    def UpdatePlaysTrakt(self):
        if self.ShowsExists('watched'):
            self.progress.update(70, line1=__getstring__(1107), line2=' ', line3=' ')
            xbmc.sleep(1000)
            print 'Checking for XBMC episodes that have higher playcount than trakt.tv'

            update_playcount = []
            trakt_imdb_index = {}
            trakt_tvdb_index = {}
            trakt_title_index = {}

            for i in range(len(self.trakt_shows['watched'])):
                if 'imdb_id' in self.trakt_shows['watched'][i]:
                    trakt_imdb_index[self.trakt_shows['watched'][i]['imdb_id']] = i

                if 'tvdb_id' in self.trakt_shows['watched'][i]:
                    trakt_tvdb_index[self.trakt_shows['watched'][i]['tvdb_id']] = i

                trakt_title_index[self.trakt_shows['watched'][i]['title']] = i

            for xbmc_show in self.xbmc_shows:
                missing = []

                #IMDB ID
                if xbmc_show['imdbnumber'].startswith('tt') and xbmc_show['imdbnumber'] in trakt_imdb_index.keys():
                    trakt_show = self.trakt_shows['watched'][trakt_imdb_index[xbmc_show['imdbnumber']]]

                #TVDB ID
                elif xbmc_show['imdbnumber'].isdigit() and xbmc_show['imdbnumber'] in trakt_tvdb_index.keys():
                    trakt_show = self.trakt_shows['watched'][trakt_tvdb_index[xbmc_show['imdbnumber']]]

                #Title
                else:
                    if xbmc_show['title'] in trakt_title_index.keys():
                        trakt_show = self.trakt_shows['watched'][trakt_title_index[xbmc_show['title']]]

                if trakt_show:
                    missing = compare_show_watched_trakt(xbmc_show, trakt_show)
                else:
                    print 'Failed to find %s on trakt.tv' % xbmc_show['title']


                if missing:
                    show = {'title': xbmc_show['title'], 'episodes': [{'episode': x['episode'], 'season': x['season']} for x in missing]}
                    
                    if xbmc_show['imdbnumber'].isdigit():
                        show['tvdb_id'] = xbmc_show['imdbnumber']
                    else:
                        show['imdb_id'] = xbmc_show['imdbnumber']

                    update_playcount.append(show)

            if update_playcount:
                print '%i shows(s) shows are missing playcounts on trakt.tv' % len(update_playcount)
                self.progress.update(75, line1=__getstring__(1107), line2='%i %s' % (len(update_playcount), __getstring__(1112)))
                xbmc.sleep(1000)

                for show in update_playcount:
                    self.progress.update(80, line1=__getstring__(1107), line2=show['title'], line3='%i %s' % (len(show['episodes']), __getstring__(1115)))
                    trakt_api('http://api.trakt.tv/show/episode/seen/'+trakt_apikey, show)

            else:
                print 'trakt.tv episode playcounts are up to date'


    def UpdatePlaysXBMC(self):
        if self.ShowsExists('watched'):
            self.progress.update(90, line1=__getstring__(1108), line2=' ', line3=' ')
            xbmc.sleep(1000)
            print 'Checking for trakt.tv episodes that have higher playcount than XBMC'

            update_playcount = []
            trakt_imdb_index = {}
            trakt_tvdb_index = {}
            trakt_title_index = {}

            for i in range(len(self.trakt_shows['watched'])):
                if 'imdb_id' in self.trakt_shows['watched'][i]:
                    trakt_imdb_index[self.trakt_shows['watched'][i]['imdb_id']] = i

                if 'tvdb_id' in self.trakt_shows['watched'][i]:
                    trakt_tvdb_index[self.trakt_shows['watched'][i]['tvdb_id']] = i

                trakt_title_index[self.trakt_shows['watched'][i]['title']] = i

            for xbmc_show in self.xbmc_shows:
                missing = []

                #IMDB ID
                if xbmc_show['imdbnumber'].startswith('tt') and xbmc_show['imdbnumber'] in trakt_imdb_index.keys():
                    trakt_show = self.trakt_shows['watched'][trakt_imdb_index[xbmc_show['imdbnumber']]]

                #TVDB ID
                elif xbmc_show['imdbnumber'].isdigit() and xbmc_show['imdbnumber'] in trakt_tvdb_index.keys():
                    trakt_show = self.trakt_shows['watched'][trakt_tvdb_index[xbmc_show['imdbnumber']]]

                #Title
                else:
                    if xbmc_show['title'] in trakt_title_index.keys():
                        trakt_show = self.trakt_shows['watched'][trakt_title_index[xbmc_show['title']]]

                if trakt_show:
                    missing = compare_show_watched_xbmc(xbmc_show, trakt_show)
                else:
                    print 'Failed to find %s on trakt.tv' % xbmc_show['title']


                if missing:
                    show = {'title': xbmc_show['title'], 'episodes': [{'episodeid': x['episodeid'], 'playcount': 1} for x in missing]}
                    update_playcount.append(show)

            if update_playcount:
                print '%i shows(s) shows are missing playcounts on XBMC' % len(update_playcount)
                self.progress.update(92, line1=__getstring__(1108), line2='%i %s' % (len(update_playcount), __getstring__(1113)))
                xbmc.sleep(1000)

                for show in update_playcount:
                    self.progress.update(95, line1=__getstring__(1108), line2=show['title'], line3='%i %s' % (len(show['episodes']), __getstring__(1115)))

                    for episode in show['episodes']:
                        xbmc_json({"jsonrpc": "2.0", "method": "VideoLibrary.SetEpisodeDetails", "params": episode, "id": 0})

            else:
                print 'XBMC episode playcounts are up to date'


    def Run(self):
        self.GetFromXBMC()

        if get_bool('add_episodes_to_trakt'):
            self.GetCollectionFromTrakt()
            self.AddToTrakt()

        if get_bool('xbmc_episode_playcount') or get_bool('trakt_episode_playcount'):
            self.GetWatchedFromTrakt()

        if get_bool('trakt_episode_playcount'):
            self.UpdatePlaysTrakt()

        if get_bool('xbmc_episode_playcount'):
            self.UpdatePlaysXBMC()

        self.progress.update(100, line1=' ', line2=__getstring__(1109), line3=' ')
        xbmc.sleep(1000)

        self.progress.close()

if __name__ == '__main__':
    if get_bool('add_movies_to_trakt') or get_bool('trakt_movie_playcount') or get_bool('xbmc_movie_playcount'):
        movies = SyncMovies()
        movies.Run()

    if get_bool('add_episodes_to_trakt') or get_bool('trakt_episode_playcount') or get_bool('xbmc_episode_playcount'):
        episodes = SyncEpisodes()
        episodes.Run()

