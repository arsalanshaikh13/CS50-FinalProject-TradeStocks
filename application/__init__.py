#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib
import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from flask_session import Session
from application.helpers import usd

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS']= False
app.config['SQLALCHEMY_DATABASE_URI']= 'sqlite:///finance_stocks.db'
app.config['SECRET_KEY'] = 'any random string'

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
# To format a value as a US dollar value (with cents listed to two decimal places), you can use the usd filter in your Jinja templates (printing values as {{ value | usd }} instead of {{ value }}.
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQLAlchemy(app)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


from application import routes