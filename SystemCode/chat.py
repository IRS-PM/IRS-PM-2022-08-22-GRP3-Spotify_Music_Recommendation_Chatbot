from flask import Flask, request, make_response, jsonify, redirect, session
from flask import render_template, Blueprint
import os
import pandas as pd
from CallDialogflow import create_session, process_usertext
from flask_login import login_required, current_user
from recommendation import *
from app import *
chat = Blueprint('chat', __name__)
# 文本为1，超链接为2，图片为3，音频为4,playlist标签为5，music标签为6

def recFromPlaylist():
    returnArray = []

    REC_top10= recommendation(spotify_df=spotify_df,
                               complete_feature_set=complete_feature_set,
                               sp=sp,
                               list_name=session["whole_playlist"],
                               playlist_name=session["current_playlist"])
    session["REC_top10"] = REC_top10[['id', 'name']].to_dict()
    music_list = list(REC_top10.name)
    t = session["current_playlist"]
    returnArray.append([1, f"this is my recommendation, according to your playlist:{t}, you may get a "
                           f"demo of one of them by clicking its name"])
    returnArray.append([6, music_list])
    return returnArray

@chat.route("/indexx")
@login_required
def indexx():

    return render_template("indexx.html")


@chat.route("/get")
def get_bot_response():
    userText = request.args.get('msg')
    returnArray = []
    session["intent"], parameters, response_txt = process_usertext(session_client=session_client, session=df_session,
                                                                   usertext=userText,
                                                                   language_code=DIALOGFLOW_LANGUAGE_CODE)
    if session["intent"] == 'recommendation':
        if parameters['Playlist'].string_value != '' and not session.get('current_playlist'):
            returnArray.append([1, "These are your playlist, which one do you want recommendation from?"])
            session["whole_playlist"] = extract_playlist(sp)
            returnArray.append([5, list(session["whole_playlist"].keys())])
        elif parameters['Playlist'].string_value != '' and session.get('current_playlist'):
            session["whole_playlist"] = extract_playlist(sp)
            returnArray = recFromPlaylist()
        else:
            music_name = parameters['music-name'].string_value if parameters['music-name'].string_value != '' else None
            music_artist = parameters['music-artist'].string_value if parameters['music-artist'].string_value != '' else None
            music_genre = parameters['music-genre'].string_value if parameters['music-genre'].string_value != '' else ''

            music_name_id = sp.search(q=music_name.replace(" ", "+"), type='track', limit=1)['tracks']['items'][0]['id'] if music_name else ''
            music_artist_id = sp.search(q=music_artist.replace(" ", "+"), type='artist', limit=1)['artists']['items'][0]['id'] if music_artist else ''

            if music_genre:
                rec_result = sp.recommendations(seed_artists=[music_artist_id], seed_tracks=[music_name_id],
                                                seed_genres=[music_genre.lower()], limit=5)
            else:
                rec_result = sp.recommendations(seed_artists=[music_artist_id], seed_tracks=[music_name_id], limit=5)

            session["track_dict"] = {track['name']: track['id'] for track in rec_result['tracks']}
            returnArray.append([1, "These are my recommendation, click the button to get a short preview!"])
            returnArray.append([7, list(session["track_dict"].keys())])

    elif session["intent"] == 'AddToPlaylist':
        if not session.get('current_playlist'):
            returnArray.append([1, "Please choose your playlist first and try again."])
            session["whole_playlist"] = extract_playlist(sp)
            returnArray.append([5, list(session["whole_playlist"].keys())])
            return jsonify(returnArray)
        add_song = parameters['music-name'].string_value
        if session.get("REC_top10"):
            music_list = {song[1].lower(): song[0] for song in session["REC_top10"]['name'].items()}
        else:
            music_list = None
        if music_list != None and add_song.lower() in list(music_list.keys()):
            music_list = {song[1].lower(): song[0] for song in session["REC_top10"]['name'].items()}
            add_song_no = music_list[add_song.lower()]
            add_song_id = session["REC_top10"]["id"][add_song_no]
            FLAG = False
            FLAG = add_to_playlist(sp,
                                   id_name=session["whole_playlist"],
                                   playlist_name=session["current_playlist"],
                                   liked_song_id=add_song_id)
            if not FLAG:
                returnArray.append([1, "Sorry, I can't add this to your playlist currently due to some unknown "
                                       "reasons, plz try again later"])
            else:
                returnArray.append([1, f"Successfully add {add_song} to your chosen playlist"])
        else:
            query = add_song.replace(" ", "+")
            search_result = sp.search(q=query, limit=1)
            add_song_id = search_result['tracks']['items'][0]['id']
            FLAG = False
            FLAG = add_to_playlist(sp,
                                   id_name=session["whole_playlist"],
                                   playlist_name=session["current_playlist"],
                                   liked_song_id=add_song_id)
            if not FLAG:
                returnArray.append([1, "Sorry, I can't add this to your playlist currently due to some unknown "
                                       "reasons, plz try again later"])
            else:
                returnArray.append(
                    [1, f"Successfully add {parameters['music-name'].string_value} to your chosen playlist"])
    elif session["intent"] == 'SetPlaylist':
        returnArray.append([1, "These are your playlist, please choose one."])
        whole_playlist = extract_playlist(sp)
        returnArray.append([5, list(whole_playlist.keys())])

    elif session["intent"] == "Default Welcome Intent":
        returnArray.append([1, response_txt])
    else:
        returnArray.append([1, "Sorry, I didn't get it, could you please say that in a clearer way?"])
    response_body = jsonify(returnArray)
    return response_body

@chat.route("/getPlaylist")
def get_bot_responsePlaylist():
    returnArray = []
    userText = request.args.get('msg')
    session["current_playlist"] = userText
    if session["intent"] == 'recommendation':
        returnArray = recFromPlaylist()
    else:
        returnArray.append([1, f"chosen playlist successfully set to: {userText}"])
    response_body = jsonify(returnArray)
    return response_body


@chat.route("/getMusics")
def get_bot_responseMusics():
    userText = request.args.get('msg')
    returnArray = []
    liked_song = userText
    music_list = {song[1]: song[0] for song in session["REC_top10"]['name'].items()}
    liked_song_no = music_list[liked_song]
    liked_song_id = session["REC_top10"]['id'][liked_song_no]
    track = sp.track(track_id=liked_song_id)
    if track['preview_url'] is None:
        returnArray.append([1, f"I'm sorry I can't find a preview for {liked_song}, but you can check the "
                               f"song on Spotify directly through this URL: \n {track['external_urls']['spotify']}"])
    else:
        returnArray.append([1, f"Here is the preview of {liked_song}, enjoy it"])
        returnArray.append([4, track['preview_url']])
    response_body = jsonify(returnArray)
    return response_body

@chat.route("/getRecommend")
def get_bot_responseSpotifyMusics():
    returnArray = []
    userText = request.args.get('msg')
    chosen_music = userText
    chosen_music_id = session["track_dict"][chosen_music]
    track = sp.track(track_id=chosen_music_id)
    if track['preview_url'] is None:
        returnArray.append([1, f"I'm sorry I can't find a preview for {chosen_music}, but you can check the "
                               f"song on Spotify directly through this URL: \n {track['external_urls']['spotify']}"])
    else:
        returnArray.append([1, f"Here is the preview of {chosen_music}, enjoy it"])
        returnArray.append([4, track['preview_url']])
    response_body = jsonify(returnArray)
    return response_body





