from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import pymysql
import os
from recommendation import *
from CallDialogflow import *
pymysql.install_as_MySQLdb()

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()

with open('Spotify_Client.txt','r', encoding='utf-8') as infile:
    client = []
    for line in infile:
        data_line = line.strip('\n').split("'")
        client.append(data_line[-2])

# client_id = 'ab8498c7f0164300a6721bd3f27dac3b'
# client_secret = '3d0f94c38e70432abc00b6d195cd6b77'
client_id = client[0]
client_secret = client[1]
user_name = 'spotify'
sp = spotify_API_access(user_name=user_name, client_id=client_id, client_secret=client_secret)
DIALOGFLOW_PROJECT_ID, DIALOGFLOW_LANGUAGE_CODE, GOOGLE_APPLICATION_CREDENTIALS = read_dialogflow()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

# DIALOGFLOW_PROJECT_ID = 'irsproject-hlxj'
# DIALOGFLOW_LANGUAGE_CODE = 'en'
SESSION_ID = os.urandom(5)
session_client, df_session = create_session(project_id=DIALOGFLOW_PROJECT_ID,
                                         session_id=SESSION_ID)
#
spotify_df = pd.read_csv('draft.csv', index_col=0)
complete_feature_set = pd.read_csv('complete_feature_set.csv', index_col=0)



def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root@localhost:3306/dbtest'

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        return User.query.get(int(user_id))

    # blueprint for auth routes in our app
    from auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from main_page import main_page as main_blueprint
    app.register_blueprint(main_blueprint)

    from chat import chat as chat_blueprint
    app.register_blueprint(chat_blueprint)

    return app