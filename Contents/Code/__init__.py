import oauth2 as oauth
import urllib
import cgi
import os

CONSUMER_KEY = 'ws3sq4zta6hzkfasq6nxrnfe'
CONSUMER_SECRET = 'juRRc6DYyD'

TRACK_URL = 'http://mikedecaro.com/site/rdio/index.htm?%s&%s'

ART  = 'art-default.jpg'
ICON = 'icon-default.png'
ICON_PREFS = 'icon-prefs.png'

####################################################################################################
def Start():

    Plugin.AddPrefixHandler("/music/rdio", MainMenu, 'Rdio', ICON, ART)

    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    MediaContainer.title1 = 'Rdio'
    MediaContainer.viewGroup = "List"
    MediaContainer.art = R(ART)
    
    DirectoryItem.thumb = R(ICON)
    WebVideoItem.thumb = R(ICON)
    
    HTTP.CacheTime = CACHE_1HOUR
    HTTP.Headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_7; en-us) AppleWebKit/533.20.25 (KHTML, like Gecko) Version/5.0.4 Safari/533.20.27'
        
    SavePlaybackToken()

####################################################################################################
def MainMenu():
    dir = MediaContainer(viewGroup="InfoList", noCache=True)

    if not CheckLoggedIn():
        Data.Remove('AccessToken')
        Data.Remove('AccessPin')
        Data.Remove('RequestToken')

    ACCESS_TOKEN = Data.LoadObject('AccessToken')
    
    if not ACCESS_TOKEN:
        #dir.Append(Function(DirectoryItem(LinkAccount, title="Link Rdio Account", subtitle="", summary="Clicking this will launch a web browser that will display a four digit number. Save this number and click Enter Pin.", thumb=R(ICON))))
        #dir.Append(Function(InputDirectoryItem(FinishLinking, title="Enter Pin", summary="Finish linking Rdio to Plex by entering the pin that is displayed on the website.", prompt='Enter the pin displayed on the Rdio website.', thumb=R(ICON))))
        dir.Append(Function(DirectoryItem(LogIn, title="Sign in to Rdio", summary="", thumb=R(ICON))))
        dir.Append(PrefsItem(title='Set Username/Password', thumb=R(ICON_PREFS)))
    else:
        dir.Append(Function(DirectoryItem(CollectionMenu, title="Collection", subtitle="", summary="", thumb=R(ICON))))
        dir.Append(Function(DirectoryItem(PlaylistsMenu, title="Playlists", subtitle="", summary="", thumb=R(ICON))))
        dir.Append(Function(DirectoryItem(HeavyRotationMenu, title="Heavy Rotation", subtitle="Your Network", summary="", thumb=R(ICON)), network=None))
        dir.Append(Function(DirectoryItem(NewReleasesMenu, title="New Releases", subtitle="", summary="", thumb=R(ICON)), timeframe=None))
        dir.Append(Function(DirectoryItem(TopChartsMenu, title="Top Charts", subtitle="", summary="", thumb=R(ICON)), type=None))
        dir.Append(Function(DirectoryItem(ClearSettings, title="Sign out of Rdio", summary='', thumb=R(ICON))))
    
    return dir

####################################################################################################
def ClearSettings(sender):
    Data.Remove('AccessToken')
    Data.Remove('AccessPin')
    Data.Remove('RequestToken')

####################################################################################################
# timeframe, "thisweek", "lastweek" or "twoweeks"
def NewReleasesMenu(sender, timeframe):
    dir = MediaContainer(viewGroup="InfoList", title2="New Releases")
    
    if not timeframe or len(timeframe) == 0:
        
        dir.Append(Function(DirectoryItem(NewReleasesMenu, title="This Week", subtitle="", summary="", thumb=R(ICON)), timeframe="thisweek"))
        dir.Append(Function(DirectoryItem(NewReleasesMenu, title="Last Week", subtitle="", summary="", thumb=R(ICON)), timeframe="lastweek"))
        dir.Append(Function(DirectoryItem(NewReleasesMenu, title="Two Weeks Ago", subtitle="", summary="", thumb=R(ICON)), timeframe="twoweeks"))
        
    else:
        
        result = GetRdioResponse('getNewReleases',{'time': timeframe, 'count': 20})
    
        for s in result['result']:
            if s['canStream'] or s['canSample']:
                dir.Append(Function(DirectoryItem(SongsMenu, title=s['name'], subtitle=s['artist'], summary="", thumb=Function(GetThumb, url=s['icon'])), artistKey=s['artistKey'], albumKey=s['key'], menuTitle="New Releases"))
        
        if len(dir) == 0:
            return MessageContainer('New Releases', 'No new releases.')
     
    return dir
    
####################################################################################################
def PlaylistsMenu(sender):
    dir = MediaContainer(viewGroup="InfoList", title2="Playlist")
    
    result = GetRdioResponse('getPlaylists', {'extras': 'trackKeys'})
    
    PopulatePlaylistsMenu(dir, result['result']['owned'], 'Yours')
    PopulatePlaylistsMenu(dir, result['result']['collab'], 'Collaborations')
    PopulatePlaylistsMenu(dir, result['result']['subscribed'], 'Subscribed')
    
    if len(dir) == 0:
        return MessageContainer('Playlists', 'No available playlists.')
    else:
        return dir
    
####################################################################################################
# Requires extra trackKeys
def PopulatePlaylistsMenu(dir, trackList, desc):
    PLAYBACK_TOKEN = Data.LoadObject('PlaybackToken')
    
    for s in trackList:
        trackIds = ''
        for t in s['trackKeys']:
            trackIds += ('trackId=%s&' % t)
        trackIds = trackIds[:-1]
        
        Log(TRACK_URL % (PLAYBACK_TOKEN, trackIds))
        dir.Append(WebVideoItem(TRACK_URL % (PLAYBACK_TOKEN, trackIds), title=s['name'], subtitle=desc, summary='', thumb=R(ICON)))
    

####################################################################################################
def CollectionMenu(sender):
    dir = MediaContainer(viewGroup="InfoList", title2="Collection")
    
    result = GetRdioResponse('getArtistsInCollection', {})
    
    for s in result['result']:
        dir.Append(Function(DirectoryItem(CollectionAlbumsMenu, title=s['name'], subtitle="", summary="", thumb=Function(GetThumb, url=s['icon'])), arg=s['key']))
    
    return dir
    
####################################################################################################
def CollectionAlbumsMenu(sender, arg):
    dir = MediaContainer(viewGroup="InfoList", title2="Collection")
    
    result = GetRdioResponse('getAlbumsForArtistInCollection', {'artist': arg})
    
    for s in result['result']:
        if s['canStream'] or s['canSample']:
            dir.Append(Function(DirectoryItem(CollectionSongsMenu, title=s['name'], subtitle="", summary="", thumb=Function(GetThumb, url=s['icon'])), arg=s['key']))
    
    if len(dir) == 0:
        return MessageContainer('Albums', 'No available albums.')
    else:
        return dir
    
####################################################################################################
def CollectionSongsMenu(sender, arg):
    dir = MediaContainer(viewGroup="InfoList", title2="Collection")
    
    result = GetRdioResponse('getTracksForAlbumInCollection', {'album': arg})
    Log(result)
    PLAYBACK_TOKEN = Data.LoadObject('PlaybackToken')
    
    trackIds = ''
    for s in result['result']:
        trackIds += ('trackId=%s&' % s['key'])
    trackIds = trackIds[:-1]
    Log(TRACK_URL % (PLAYBACK_TOKEN, trackIds));
    dir.Append(WebVideoItem(TRACK_URL % (PLAYBACK_TOKEN, trackIds), title='Play All', summary='', thumb=R(ICON)))
    
    for s in result['result']:
        if s['canStream'] or s['canSample']:
            trackId = 'trackId=%s' % s['key']
            Log(TRACK_URL % (PLAYBACK_TOKEN, trackId));
            dir.Append(WebVideoItem(TRACK_URL % (PLAYBACK_TOKEN, trackId), title=s['name'], summary='', subtitle='', thumb=Function(GetThumb, url=s['icon'])))
    
    if len(dir) == 1:
        return MessageContainer('Songs', 'No available songs.')
    else:
        return dir

####################################################################################################
def SongsMenu(sender, artistKey, albumKey, menuTitle):
    dir = MediaContainer(viewGroup="InfoList", title2=menuTitle)
    
    result = []
    
    allResults = GetRdioResponse('getAlbumsForArtist', {'artist': artistKey, 'extras': 'tracks'})
    Log(allResults)
    for s in allResults['result']:
        if s['key'] == albumKey:
            result = s['tracks']
            break
    
    PopulateSongsMenu(dir, result)
    
    if len(dir) == 1:
        return MessageContainer('Songs', 'No available songs.')
    else:
        return dir
   
####################################################################################################
def PopulateSongsMenu(dir, trackList):
    PLAYBACK_TOKEN = Data.LoadObject('PlaybackToken')
    
    trackIds = ''
    for s in trackList:
        trackIds += ('trackId=%s&' % s['key'])
    trackIds = trackIds[:-1]
    Log(TRACK_URL % (PLAYBACK_TOKEN, trackIds));
    dir.Append(WebVideoItem(TRACK_URL % (PLAYBACK_TOKEN, trackIds), title='Play All', summary='', thumb=R(ICON)))
    
    for s in trackList:
        if s['canStream'] or s['canSample']:
            trackId = 'trackId=%s' % s['key']
            Log(TRACK_URL % (PLAYBACK_TOKEN, trackId));
            dir.Append(WebVideoItem(TRACK_URL % (PLAYBACK_TOKEN, trackId), title=s['name'], summary='', subtitle='', thumb=Function(GetThumb, url=s['icon'])))
    

####################################################################################################
# network, "you", "yournetwork" or "everyone"
def HeavyRotationMenu(sender, network):
    dir = MediaContainer(viewGroup="InfoList", title2="Heavy Rotation")
    
    if not network or len(network) == 0:
        
        dir.Append(Function(DirectoryItem(HeavyRotationMenu, title="You", subtitle="", summary="", thumb=R(ICON)), network="you"))
        dir.Append(Function(DirectoryItem(HeavyRotationMenu, title="Your Network", subtitle="", summary="", thumb=R(ICON)), network="yournetwork"))
        dir.Append(Function(DirectoryItem(HeavyRotationMenu, title="Everyone", subtitle="", summary="", thumb=R(ICON)), network="everyone"))
        
    else:
        
        if network == "everyone":
            argList = {'type': 'albums', 'friends': 'true', 'limit': 12}
        else:
            userKey = Data.LoadObject('UserKey')
            if network == "yournetwork":
                argList = {'user': userKey, 'type': 'albums', 'friends': 'true', 'limit': 12}
            else:
                argList = {'user': userKey, 'type': 'albums', 'friends': 'false', 'limit': 12}
        
        result = GetRdioResponse('getHeavyRotation', argList)
        
        for s in result['result']:
            if s['canStream'] or s['canSample']:
                dir.Append(Function(DirectoryItem(SongsMenu, title=s['name'], subtitle=s['artist'], summary="", thumb=Function(GetThumb, url=s['icon'])), artistKey=s['artistKey'], albumKey=s['key'], menuTitle="Heavy Rotation"))
        
    return dir

####################################################################################################
# type, "Album", "Track" or "Playlist"
def TopChartsMenu(sender, type):
    dir = MediaContainer(viewGroup="InfoList", title2="Top Charts")
    
    if not type or len(type) == 0:
        
        dir.Append(Function(DirectoryItem(TopChartsMenu, title="Top Albums", subtitle="", summary="", thumb=R(ICON)), type="Album"))
        dir.Append(Function(DirectoryItem(TopChartsMenu, title="Top Songs", subtitle="", summary="", thumb=R(ICON)), type="Track"))
        dir.Append(Function(DirectoryItem(TopChartsMenu, title="Top Playlists", subtitle="", summary="", thumb=R(ICON)), type="Playlist"))
        
    else:
        
        if type == "Album":
            
            result = GetRdioResponse('getTopCharts', {'type': type, 'count': 20})
            
            for s in result['result']:
                if s['canStream'] or s['canSample']:
                    dir.Append(Function(DirectoryItem(SongsMenu, title=s['name'], subtitle=s['artist'], summary="", thumb=Function(GetThumb, url=s['icon'])), artistKey=s['artistKey'], albumKey=s['key'], menuTitle="Top Charts"))
            
            if len(dir) == 0:
                return MessageContainer('Albums', 'No available albums.')
                
        elif type == "Track":
            
            result = GetRdioResponse('getTopCharts', {'type': type, 'count': 20})
            
            PopulateSongsMenu(dir, result['result'])
            
            if len(dir) == 1:
                return MessageContainer('Songs', 'No available songs.')
            
        elif type == "Playlist":
        
            result = GetRdioResponse('getTopCharts', {'type': type, 'count': 20, 'extras': 'trackKeys'})
            
            PopulatePlaylistsMenu(dir, result['result'], '')
            
            if len(dir) == 0:
                return MessageContainer('Playlists', 'No available playlists.')
            
        
    return dir

####################################################################################################
#NON AUTOMATED LOGIN
def LinkAccount(sender):
    # create the OAuth consumer credentials
    CONSUMER = oauth.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
    
    client = oauth.Client(CONSUMER)
    response, content = client.request('http://api.rdio.com/oauth/request_token', 'POST', urllib.urlencode({'oauth_callback':'oob'}))
    parsed_content = dict(cgi.parse_qsl(content))
    
    REQUEST_TOKEN = oauth.Token(parsed_content['oauth_token'], parsed_content['oauth_token_secret'])
    
    Data.SaveObject('RequestToken', REQUEST_TOKEN)
    
    Helper.Run('open.sh', '%s?oauth_token=%s' % (parsed_content['login_url'], parsed_content['oauth_token']))

def FinishLinking(sender, query):
    REQUEST_TOKEN = Data.LoadObject('RequestToken')
    
    if REQUEST_TOKEN and len(query) > 0:
        CONSUMER = oauth.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
        
        # associate the verifier with the request token
        REQUEST_TOKEN.set_verifier(query)
        
        # upgrade the request token to an access token
        client = oauth.Client(CONSUMER, REQUEST_TOKEN)
        response, content = client.request('http://api.rdio.com/oauth/access_token', 'POST')
        parsed_content = dict(cgi.parse_qsl(content))
        ACCESS_TOKEN = oauth.Token(parsed_content['oauth_token'], parsed_content['oauth_token_secret'])

        Data.SaveObject('AccessToken', ACCESS_TOKEN)
        
        SavePlaybackToken()
    elif not requestToken:
        return MessageContainer('Invalid Pin', 'Please link your account first.')
    elif len(query) == 0:
        return MessageContainer('Invalid Pin', 'You entered an invalid pin.')

####################################################################################################
def GetThumb(url):
    if url:
        try:
            data = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
            return DataObject(data, 'image/jpeg')
        except:
            pass

    return Redirect(R(ICON))
    
####################################################################################################
def SavePlaybackToken():
    ACCESS_TOKEN = Data.LoadObject('AccessToken')
    
    if ACCESS_TOKEN:
        CONSUMER = oauth.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
        
        client = oauth.Client(CONSUMER, ACCESS_TOKEN)
        response = client.request('http://api.rdio.com/1/', 'POST', urllib.urlencode({'method': 'getPlaybackToken', 'domain': 'mikedecaro.com'}))
        result = JSON.ObjectFromString(response[1])
        Data.SaveObject('PlaybackToken', 'playbackToken=%s' % result['result'])

####################################################################################################
def CheckLoggedIn():
    ACCESS_TOKEN = Data.LoadObject('AccessToken')
    
    if ACCESS_TOKEN:
        result = GetRdioResponse('currentUser', {'extras':'isSubscriber'})
        
        if result['result']['isSubscriber'] == False:
            Data.SaveObject('UserKey', result['result']['key'])
            return 'Free'
        else:
            Data.SaveObject('UserKey', result['result']['key'])
            return 'True'
            
    Data.Remove('UserKey')

####################################################################################################
#AUTOMATED LOGIN
def LogIn(sender):
    if not Prefs['rdio_user'] or not Prefs['rdio_pass']:
        return MessageContainer('Credentials', 'Please enter your username and password.')
    elif len(Prefs['rdio_user']) == 0 or len(Prefs['rdio_pass']) == 0:
        return MessageContainer('Credentials', 'Please enter your username and password.')
    
    # create the OAuth consumer credentials
    CONSUMER = oauth.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
    
    client = oauth.Client(CONSUMER)
    response, content = client.request('http://api.rdio.com/oauth/request_token', 'POST', urllib.urlencode({'oauth_callback':'oob'}))
    parsed_content = dict(cgi.parse_qsl(content))
    
    REQUEST_TOKEN = oauth.Token(parsed_content['oauth_token'], parsed_content['oauth_token_secret'])
    
    AUTH_URL = '%s?oauth_token=%s' % (parsed_content['login_url'], parsed_content['oauth_token'])
    
    response = HTTP.Request(AUTH_URL)
    
    if str(response).find('login_form') > -1:
        postValues = {'email':Prefs['rdio_user'], 'password': Prefs['rdio_pass']}
        response = HTTP.Request(AUTH_URL, values=postValues)
        if str(response).find('<li>auth</li>') > -1:
            return MessageContainer('Credentials', 'Invalid username/password.')
        elif str(response).find('login_form') > -1:
            return MessageContainer('Error', 'Couldn\'t log in.')
            
    xmlObject = HTML.ElementFromString(str(response))
    verifier = xmlObject.xpath("//input[@name='verifier']")[0].value
    
    postValues = {'oauth_token':parsed_content['oauth_token'], 'verifier':verifier, 'approve': ''}
    response = HTTP.Request(AUTH_URL, values=postValues)
    
    xmlObject = HTML.ElementFromString(str(response))
    ACCESS_PIN = xmlObject.xpath("//strong")[0].text
    
    # associate the verifier with the request token
    REQUEST_TOKEN.set_verifier(ACCESS_PIN)
    
    # upgrade the request token to an access token
    client = oauth.Client(CONSUMER, REQUEST_TOKEN)
    response, content = client.request('http://api.rdio.com/oauth/access_token', 'POST')
    parsed_content = dict(cgi.parse_qsl(content))
    ACCESS_TOKEN = oauth.Token(parsed_content['oauth_token'], parsed_content['oauth_token_secret'])
    
    Data.SaveObject('AccessToken', ACCESS_TOKEN)
    
    loggedInResult = CheckLoggedIn()
    if loggedInResult == 'True' or logedInResult == 'Free':
        SavePlaybackToken()
    else:
        return MessageContainer('Error', 'Problem logging in.')

####################################################################################################
def GetRdioResponse(methodName, args):
    methodDict = {'method': methodName}
    argList = dict(methodDict.items() + args.items())
    
    CONSUMER = oauth.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
    ACCESS_TOKEN = Data.LoadObject('AccessToken')
    
    client = oauth.Client(CONSUMER, ACCESS_TOKEN)
    response = client.request('http://api.rdio.com/1/', 'POST', urllib.urlencode(argList))
    
    result = JSON.ObjectFromString(response[1])
    
    return result
    