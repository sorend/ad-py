
import os
import logging
import urllib.parse
import urllib.request
import json
import datetime
import dateutil.parser
from apiclient.discovery import build

FLICKR_API_KEY = os.environ['FLICKR_API_KEY']
FLICKR_USERID  = os.environ['FLICKR_USERID']
YOUTUBE_DEVELOPER_KEY = os.environ['YOUTUBE_DEVELOPER_KEY']
YOUTUBE_CHANNEL = os.environ['YOUTUBE_CHANNEL']

#
# Load external data sources, should return a structure like this.
#
# [
#   { "title": "",
#     "link":  "",
#     "updated": "",
#     "thumb": "" },
#   ...
# ]
#

def load_flickr():

    def flickr_call(method, **kw):
        extra = '&'.join(map(lambda t: "%s=%s" % (str(t[0]), urllib.parse.quote_plus(str(t[1]))), kw.items()))
        if len(extra) > 0:
            extra = '&' + extra
        url = 'https://api.flickr.com/services/rest/?api_key=%s&user_id=%s&format=json&nojsoncallback=1&method=%s%s' % (FLICKR_API_KEY, FLICKR_USERID, method, extra)

        return json.load(urllib.request.urlopen(url))

    def extract(e):

        psid, prid, farm, server, secret = e["id"], e["primary"], e["farm"], e["server"], e["secret"]
        link = 'https://www.flickr.com/photos/sorend/sets/%s/' % psid
        thumb = 'https://farm%s.static.flickr.com/%s/%s_%s_m.jpg' % (farm, server, prid, secret)
        updated = str(datetime.datetime.fromtimestamp(int(e["date_update"])))

        return {
            "id": "flickr-%s" % (psid,),
            "title": e["title"]["_content"],
            "link": link,
            "updated": updated,
            "thumb": thumb
        }

    logging.info("getting flickr photosets")
    result = flickr_call('flickr.photosets.getList', primary_photo_extras="last_update,url_m")

    return [extract(e) for e in result["photosets"]["photoset"]]

def load_youtube():

    youtube = build("youtube", "v3", developerKey=YOUTUBE_DEVELOPER_KEY,
                    cache_discovery=False)

    logging.info("getting youtube channel")
    channels_response = youtube.channels().list(
        # forUsername="sorend",  # this is the old channel
        id=YOUTUBE_CHANNEL,  #  this is the current one.
        part="contentDetails"
    ).execute()

    response = []
    for channel in channels_response["items"]:
        uploads_list_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]

        playlist_list_request = youtube.playlistItems().list(
            playlistId=uploads_list_id,
            part="snippet",
            maxResults=50
        )

        while playlist_list_request:
            playlist_list_response = playlist_list_request.execute()

            for playlist_item in playlist_list_response["items"]:
                video_id = playlist_item["snippet"]["resourceId"]["videoId"]
                obj = {
                    "id": "youtube-%s" % (video_id,),
                    "title": playlist_item["snippet"]["title"].replace("_", " "),
                    "link" : "https://youtu.be/%s" % (video_id,),
                    "updated" : dateutil.parser.parse(playlist_item["snippet"]["publishedAt"]).strftime("%Y-%m-%d %H:%M:%S"),
                    "thumb": playlist_item["snippet"]["thumbnails"]["medium"]["url"]
                }
                response.append(obj)

            playlist_list_request = youtube.playlistItems().list_next(
                playlist_list_request, playlist_list_response)
    
    return response

# loaders
loaders = (load_flickr, load_youtube)

