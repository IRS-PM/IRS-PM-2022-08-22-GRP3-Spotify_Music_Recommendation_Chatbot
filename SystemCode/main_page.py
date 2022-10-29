from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app import db

main_page = Blueprint('main_page', __name__)

@main_page.route('/')
def index():
    return render_template('index.html')

# @main_page.route('/profile')
# @login_required
# def profile():
#     return render_template('profile.html', name=current_user.name)

