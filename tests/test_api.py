from NEMbox.api import NetEase
from NEMbox.api import Parse


def test_api():
    api = NetEase()
    ids = [347230, 496619464, 405998841, 28012031]
    print(api.songs_url(ids))
    print(api.songs_detail(ids))
    print(Parse.song_url(api.songs_detail(ids)[0]))
    # user = api.login('example@163.com', md5(b'').hexdigest())
    # user_id = user['account']['id']
    # print(user)
    # api.logout()
    # print(api.user_playlist(3765346))
    # print(api.song_comments(347230))
    # print(api.search('海阔天空')['result']['songs'])
    # print(api.top_songlist()[0])
    # print(Parse.song_url(api.top_songlist()[0]))
    # print(api.djchannels())
    # print(api.search('测', 1000))
    # print(api.album(38721188))
    # print(api.djchannels()[:5])
    # print(api.channel_detail([348289113]))
    # print(api.djprograms(243, True, limit=5))
    # print(api.request('POST', '/weapi/djradio/hot/v1', params=dict(
    #     category='旅途|城市',
    #     limit=5,
    #     offset=0
    # )))
    # print(api.recommend_resource()[0])
    print(api.songs_url([561307346]))
