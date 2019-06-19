from Depend import *
from user import user
import base64
import re,os
from email.mime.multipart import MIMEMultipart
import datetime
from email.mime.text import MIMEText
from flask_jwt_extended import (jwt_required, get_jwt_identity)
import smtplib
from mailer import Message
from mongoConnection import MongoDB
from Config import Configuration
import ast
from flask import Flask,sessions
import requests
import json
from logger import generate_log
import mongodb

class TWSApiTest(Resource):
    def __init__(self):
        self.name = "TWSAPI"

    def post(self):
        data = json.loads(request.data.decode())
        action = data["action"]