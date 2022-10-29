import spotipy
import spotipy.util as util
import pandas as pd
from spotipy import SpotifyOAuth
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
from skimage import io
import warnings
import random
warnings.filterwarnings("ignore")


def spotify_API_access(user_name, client_id, client_secret):
    """

    :param user_name: spotify user name
    :param client_id: the client id
    :param client_secret: the client secret
    :return: the interface of spotify web API
    """
    scope = 'playlist-read-private playlist-modify-private user-read-private'

    token = util.prompt_for_user_token(user_name, scope,
                                       client_id=client_id,
                                       client_secret=client_secret,
                                       # the redirect url should be added manually in your application
                                       redirect_uri='http://localhost:8881/')
    sp = spotipy.Spotify(auth=token)
    return sp

# def add_to_playlist(sp, id_name, playlist_name, liked_song_id):
#     """
#
#     :param sp: the Spotify Web API
#     :param id_name: user's playlist dic, which includes names and the corresponding IDs
#     :param playlist_name: the playlist where the liked song adds to
#     :param liked_song_id: user-liked recommandation song
#     :return: implement song adding
#     """
#     if playlist_name not in id_name.keys():
#         return f'There is no playlist named {playlist_name}'
#     liked_song_uri = [f'spotify:track:{liked_song_id}']
#     sp.playlist_add_items(id_name[playlist_name], liked_song_uri)
#     return True


def add_to_playlist(sp, id_name, playlist_name, liked_song_id):
    """

    :param sp: the Spotify Web API
    :param id_name: user's playlist dic, which includes names and the corresponding IDs
    :param playlist_name: the playlist where the liked song adds to
    :param liked_song_id: user-liked recommandation song
    :return: implement song adding
    """
    if playlist_name not in id_name.keys():
        return False
    liked_song_uri = [f'spotify:track:{liked_song_id}']
    sp.playlist_add_items(id_name[playlist_name], liked_song_uri)
    return True


def extract_playlist(sp):
    """
    Extract user's playlist

    :param sp: the Spotify Web API
    :return: user's playlist including names and cover images
    """
    dict_playlist = sp.current_user_playlists()
    id_name = {}

    for i in dict_playlist['items']:
        id_name[i['name']] = i['uri'].split(':')[2]
    playlists = ','.join(id_name.keys())
    # print(f'Here are the playlist(s) extracted:{playlists}.')
    return id_name


def create_necessary_outputs(sp, playlist_name, id_dic, df):
    """
    Pull songs from a specific playlist.

    Parameters:
        sp: the Spotify Web API
        playlist_name (str): name of the playlist you'd like to pull from the spotify API
        id_dic (dic): dictionary that maps playlist_name to playlist_id
        df (pandas dataframe): spotify dataframe

    Returns:
        playlist: all songs in the playlist THAT ARE AVAILABLE IN THE KAGGLE DATASET
    """

    # generate playlist dataframe
    playlist = pd.DataFrame()
    playlist_name = playlist_name

    for ix, i in enumerate(sp.playlist(id_dic[playlist_name])['tracks']['items']):
        # print(i['track']['artists'][0]['name'])
        playlist.loc[ix, 'artist'] = i['track']['artists'][0]['name']
        playlist.loc[ix, 'name'] = i['track']['name']
        playlist.loc[ix, 'id'] = i['track']['id']  # ['uri'].split(':')[2]
        playlist.loc[ix, 'url'] = i['track']['album']['images'][1]['url']
        playlist.loc[ix, 'date_added'] = i['added_at']

    playlist['date_added'] = pd.to_datetime(playlist['date_added'])

    playlist_in = playlist[playlist['id'].isin(df['id'].values)].sort_values('date_added', ascending=False)
    # if playlist_in.empty:
    #     playlist_in['id'] = df.at[random.randint(1,1000),'id']
    #     playlist_in['date_added'] = playlist.at[0,'date_added']


    return playlist_in


def generate_playlist_feature(complete_feature_set, playlist_df, weight_factor):
    """
    Summarize a user's playlist into a single vector

    Parameters:
        complete_feature_set (pandas dataframe): Dataframe which includes all of the features for the spotify songs
        playlist_df (pandas dataframe): playlist dataframe
        weight_factor (float): float value that represents the recency bias. The larger the recency bias, the most priority recent songs get. Value should be close to 1.

    Returns:
        playlist_feature_set_weighted_final (pandas series): single feature that summarizes the playlist
        complete_feature_set_nonplaylist (pandas dataframe):
    """

    complete_feature_set_playlist = complete_feature_set[
        complete_feature_set['id'].isin(playlist_df['id'].values)]  # .drop('id', axis = 1).mean(axis =0)
    complete_feature_set_playlist = complete_feature_set_playlist.merge(playlist_df[['id', 'date_added']], on='id',
                                                                        how='inner')
    complete_feature_set_nonplaylist = complete_feature_set[
        ~complete_feature_set['id'].isin(playlist_df['id'].values)]  # .drop('id', axis = 1)

    playlist_feature_set = complete_feature_set_playlist.sort_values('date_added', ascending=False)

    most_recent_date = playlist_feature_set.iloc[0, -1]

    for ix, row in playlist_feature_set.iterrows():
        playlist_feature_set.loc[ix, 'months_from_recent'] = int(
            (most_recent_date.to_pydatetime() - row.iloc[-1].to_pydatetime()).days / 30)

    playlist_feature_set['weight'] = playlist_feature_set['months_from_recent'].apply(lambda x: weight_factor ** (-x))

    playlist_feature_set_weighted = playlist_feature_set.copy()
    # print(playlist_feature_set_weighted.iloc[:,:-4].columns)
    playlist_feature_set_weighted.iloc[:, :-4] = pd.DataFrame(playlist_feature_set_weighted.iloc[:, :-4], dtype=float)
    playlist_feature_set_weighted.update(
        playlist_feature_set_weighted.iloc[:, :-4].mul(playlist_feature_set_weighted.weight, 0))
    playlist_feature_set_weighted_final = playlist_feature_set_weighted.iloc[:, :-4]
    # playlist_feature_set_weighted_final['id'] = playlist_feature_set['id']
    n = len(playlist_feature_set_weighted_final)
    playlist_attributes = playlist_feature_set_weighted_final.iloc[:,127:136].sum(axis = 0)/n
    playlist_feature_set_weighted_final = playlist_feature_set_weighted_final.sum(axis = 0)
    playlist_feature_set_weighted_final[127:136] = playlist_attributes

    return playlist_feature_set_weighted_final, complete_feature_set_nonplaylist


def generate_playlist_recos(sp, df, features, nonplaylist_features):
    """
    Pull songs from a specific playlist.

    Parameters:
        df (pandas dataframe): spotify dataframe
        features (pandas series): summarized playlist feature
        nonplaylist_features (pandas dataframe): feature set of songs that are not in the selected playlist

    Returns:
        non_playlist_df_top_40: Top 40 recommendations for that playlist
    """

    non_playlist_df = df[df['id'].isin(nonplaylist_features['id'].values)]
    features_vector = features.values.reshape(1, -1)
    non_playlist_df['sim'] = cosine_similarity(nonplaylist_features.drop('id', axis=1).values,
                                               features_vector)[:, 0]
    non_playlist_df_top_10 = non_playlist_df.sort_values('sim', ascending=False).head(10)
    non_playlist_df_top_10['url'] = non_playlist_df_top_10['id'].apply(
        lambda x: sp.track(x)['album']['images'][1]['url'])

    return non_playlist_df_top_10


def visualize_songs(df):
    """
    Visualize cover art of the songs in the inputted dataframe

    Parameters:
        df (pandas dataframe): Playlist Dataframe
    """

    temp = df['url'].values
    plt.figure(figsize=(15, int(0.625 * len(temp))))
    columns = 5

    for i, url in enumerate(temp):
        plt.subplot(int(len(temp) / columns + 1), columns, i + 1)
        image = io.imread(url)
        plt.imshow(image)
        plt.xticks(color='w', fontsize=0.1)
        plt.yticks(color='w', fontsize=0.1)
        plt.xlabel(df['name'].values[i], fontsize=12)
        plt.tight_layout(h_pad=0.4, w_pad=0)
        plt.subplots_adjust(wspace=None, hspace=None)

    plt.show()


def recommendation(spotify_df, complete_feature_set, sp, list_name, playlist_name):
    """

    :param spotify_df: the song dataset
    :param complete_feature_set: song feature dataset
    :param client_id: client id
    :param client_secret: client secret
    :param user_name: user name
    :return: REC_top40 (dataframe): top40 recommended songs based on user's playlist
    """
    # sp = spotify_API_access(user_name, client_id, client_secret)
    # list_name, list_photos = extract_playlist(sp)

    # playlist_name = input('please enter one playlist name:')

    playlist_in_dataset = create_necessary_outputs(sp, playlist_name, list_name, spotify_df)

    complete_feature_set_playlist_vector, complete_feature_set_nonplaylist = generate_playlist_feature(
        complete_feature_set, playlist_in_dataset, 1.09)

    REC_top40 = generate_playlist_recos(sp, spotify_df, complete_feature_set_playlist_vector,
                                        complete_feature_set_nonplaylist)
    return REC_top40.iloc[0:10]


if __name__ == '__main__':
    spotify_df = pd.read_csv('draft.csv', index_col=0)
    complete_feature_set = pd.read_csv('complete_feature_set.csv', index_col=0)

    client_id = 'ab8498c7f0164300a6721bd3f27dac3b'
    client_secret = '3d0f94c38e70432abc00b6d195cd6b77'
    user_name = '31vixbmfp6shbk76f2vdlvxyzuiq'
    REC_top40 = recommendation(spotify_df, complete_feature_set, client_id, client_secret, user_name)
