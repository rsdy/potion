from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from potion.common import cfg

app = Flask(__name__)
app.secret_key = cfg.get('app', 'secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = cfg.get('database', 'connection')
db = SQLAlchemy(app)
