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
from IbConnection import *
class user:
    def __init__(self):
        self.name = "user"
        self.ip = Configuration().GetData()['PrivateIp']
        self.port = Configuration().GetData()['MongoPort']
        self.db = Configuration().GetData()['MongoDB']
        self.email = Configuration().GetData()['EmailID']
        self.password = Configuration().GetData()['Password']
        self.reg_emailLink = Configuration().GetData()['RegisterEmail']
        self.forgot_passwordLink = Configuration().GetData()['ForgotPassword']
        self.email_ids = Configuration().GetData()['Email']
        self.sp_link = Configuration().GetData()['SP']
        self.mongoObj = MongoDB()
        self.mongoObj.ConnectMongo(self.ip, self.port, self.db)
        

    # for account registration (SignUp)
    def register(self, request):
        data = json.loads(request.data.decode())
        try:
            exists = self.mongoObj.ReadValue("users", data['email'])
            if exists != None:
                return {"msg": "Email already exist", "status": "False"}
            else:
                dic = {"user_id": data['email'], "password": data['password'], "firstname": data['firstname'],
                       'lastname': data['lastname'], "status": "0", "mobile": "", "skype": "", "phone": "", "gender": "" }
                self.mongoObj.WriteValue("users", data['email'], dic)
                # mongodb.WriteValue("users", data['email'], dic)
                email = data['email']
                message = Message(From=self.email,To=email)
                message.Subject = "Codex Email Verification"
                message.Html = """

                    <!DOCTYPE html>
                    <html>
                    <head>
                    <style>
                    

                    body{

                    font-family: sans-serif;
                    }

                    .main{

                    background-color : #f3f7fa;
                    height:300px;
                    padding: 25px 250px;

                    }
                    .main h1{

                    color : #0070c9;
                    text-align: center;

                    }
                    .sub-main{

                    padding: 25px 50px;
                    background-color:#FFF;

                    }

                    .main .sub-main h1{
                        text-align: center;
                        color : #46555d;
                        font-weight:200;
                    }
                    .main .sub-main p{

                        text-align: center;
                        color:#46555d;
                        font-size:14px;

                    }
                    .main .sub-main img{

                        display:block; margin-left:auto;margin-right:auto;width:10%;height:10%;
                    }
                    </style>
                    </head>
                    <body>


                    <div class="main" style="background-color : #f3f7fa;height:300px;padding: 25px 250px;">

                    <h1 style=" color : #0070c9;text-align: center;">Codex</h1>

                    <div class="sub-main" style="padding: 25px 50px;background-color:#FFF;">


                        <img style="display:block; margin-left:auto;margin-right:auto;width:10%;height:10%;"  src='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRqbCA0f04h_Z2mbp3qs4Yr_Zxz5Xu_l8NYUCwOJMIJK7RWWGYW' />
                        <h1 style=" text-align: center;color : #46555d;font-weight:200;">Welcome to Codex</h1>
                        <hr>
                        <p style=" text-align: center;color:#46555d;font-size:14px;">Please wait for registration approval from Codex team</p>

                    </div>
                    </div>

                    </body>
                    </html>
                    """

                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.email, self.password)
                server.sendmail(self.email, email, message.as_string())

                sender = self.email
                gmail_password = self.password
                dr_tariq_team = self.email_ids
                COMMASPACE = ', '
                recipients = dr_tariq_team

                # Create the enclosing (outer) message
                outer = MIMEMultipart()
                outer['Subject'] = 'Email Verification'
                outer['To'] = COMMASPACE.join(recipients)
                outer['From'] = sender

                message = """

                    <!DOCTYPE html>
                    <html>
                    <head>
                    <style>
                    @import url('https://fonts.googleapis.com/css?family=Open+Sans');

                    body{

                    font-family: sans-serif;
                    }

                    .main{

                    background-color : #f3f7fa;
                    height:350px;
                    padding: 25px 250px;

                    }
                    .main h1{

                    color : #0070c9;
                    text-align: center;

                    }
                    .sub-main{

                    padding: 25px 50px;
                    background-color:#FFF;

                    }

                    .main .sub-main h1{
                        text-align: center;
                        color : #46555d;
                        font-weight:200;
                    }
                    .main .sub-main p{

                        text-align: center;
                        color:#46555d;
                        font-size:14px;

                    }
                    .main .sub-main img{

                        display:block; margin-left:auto;margin-right:auto;width:10%;height:10%;
                    }
                    </style>
                    </head>
                    <body>


                    <div class="main" style=" background-color : #f3f7fa; height:350px; padding: 25px 250px;">

                    <h1 style="color : #0070c9; text-align: center;">Codex</h1>

                    <div class="sub-main" style=" padding: 25px 50px; background-color:#FFF;">


                        <img style="display:block; margin-left:auto;margin-right:auto;width:10%;height:10%;"  src='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRqbCA0f04h_Z2mbp3qs4Yr_Zxz5Xu_l8NYUCwOJMIJK7RWWGYW' />
                        <h1 style="text-align: center;color : #46555d;font-weight:200;">New Codex User</h1>
                        <hr>
                         <p style=" text-align: center;color:#46555d; font-size:14px;"> 
                                     Email Address : """ + data['email'] + """<br>
                                     Date of Registration : """ + str(datetime.datetime.now().date()) + """<br>
                                                                               Please Authorize """ + data['email'] + """  to use Codex (Stock Prediction System) by verifying him on the given link:<br>
                                                                               """ + self.reg_emailLink + (
                        str(base64.b64encode(bytes(email, "utf-8")).decode("utf-8"))).replace("=",
                                                                                              "~") + """

                    </div>
                    </div>
                    </body>
                    </html>
                    """

                # message = """<p> Email Address : """+data['email']+"""<br>
                #  Date of Registration : """ + str(datetime.datetime.now().date()) + """<br> Please Authorize """ \
                #           + data['email'] + """  to use Stock Prediction System by verifying him on the given link: <br> """ \
                #           + self.reg_emailLink + ( str(base64.b64encode(bytes(email, "utf-8")).decode("utf-8"))).replace("=", "~")

                outer.attach(MIMEText(message, 'html'))
                outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'
                composed = outer.as_string()

                # Send the email
                with smtplib.SMTP('smtp.gmail.com', 587) as s:
                    s.ehlo()
                    s.starttls()
                    s.ehlo()
                    s.login(sender, gmail_password)
                    s.sendmail(sender, recipients, composed)
                    s.close()
                print("Email sent!")
                return {"status": "True"}
        except Exception as e:
            generate_log('register', str(e), str(request))


    @jwt_required
    def update(self, request):
        data = json.loads(request.data.decode())
        try:
            userid  = get_jwt_identity()
            record = self.mongoObj.ReadValue("users", userid)
            record = ast.literal_eval(record["Data"])
            record['mobile'] = data['mobile']
            record['skype'] = data['skype']
            record['phone'] = data['phone']
            record['gender'] = data['gender']
            record['firstname'] = data['firstname']
            record['lastname'] = data['lastname']
            record['image'] = data['image']
            self.mongoObj.UpdateValue("users", userid, record)
            record['password'] = ""
            record['msg'] = "successfully Updated Data, status : True"
            return record
        except Exception as e:
            generate_log('update', str(e), str(request))
            return {"msg": "invalid walletID","status": "False"}

    @jwt_required
    def history(self, request):
        data = json.loads(request.data.decode())
        try:
            userid = get_jwt_identity()
            exists = self.mongoObj.ReadValue("history", userid)
            if exists != None:
                self.mongoObj.UpdateValue("history", userid, data)
                print("successfully Updated Data, status : True")
            else:
                self.mongoObj.WriteValue("history", userid, data)
                print("successfully Added Data, status : True")
            return {"status": "True"}
        except Exception as e:
            generate_log('history', str(e), str(request))
            return {"msg": "History Can not able to maintain", "status": "False"}

    def verify(self, request):
        data = json.loads(request.data.decode())
        try:
            email = base64.b64decode((bytes(str(data["email"]).replace("~", "="), "utf-8"))).decode("utf-8")
            record = self.mongoObj.ReadValue("users", email)
            if (record != None):
                record = ast.literal_eval(record["Data"])
                record["status"] = "1"
                self.mongoObj.UpdateValue("users", email, record)
                message = Message(From=self.email,
                                  To=email)
                message.Subject = "Stock Prediction Account Approved"

                # message.Html = """<p>Dear """+ record['firstname'] + """!<br>
                #                                                            Your Stock Prediction System account has been approved successfully<br>
                #                                                            Here is the link """ + self.sp_link + """  to Access SP System"""

                message.Html = """

                <!DOCTYPE html>
                <html>
                <head>
                <style>
                @import url('https://fonts.googleapis.com/css?family=Open+Sans');

                body{

                font-family: sans-serif;
                }

                .main{

                background-color : #f3f7fa;
                height:300px;
                padding: 25px 250px;

                }
                .main h1{

                color : #0070c9;
                text-align: center;

                }
                .sub-main{

                padding: 25px 50px;
                background-color:#FFF;

                }

                .main .sub-main h1{
                    text-align: center;
                    color : #46555d;
                    font-weight:200;
                }
                .main .sub-main p{

                    text-align: center;
                    color:#46555d;
                    font-size:14px;

                }
                .main .sub-main img{

                    display:block; margin-left:auto;margin-right:auto;width:10%;height:10%;
                }
                </style>
                </head>
                <body>


                <div class="main" style=" background-color : #f3f7fa;height:300px; padding: 25px 250px;">

                <h1 style="color : #0070c9;text-align: center;">Codex</h1>

                <div class="sub-main" style="padding: 25px 50px; background-color:#FFF;">

                    <img style="display:block; margin-left:auto;margin-right:auto;width:10%;height:10%;" src='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRqbCA0f04h_Z2mbp3qs4Yr_Zxz5Xu_l8NYUCwOJMIJK7RWWGYW' />
                    <h1 style="text-align: center;color : #46555d;font-weight:200;">Account Approved</h1>
                    <hr>
                    <p style="  text-align: center;color:#46555d;font-size:14px;"><b>Dear """ + record['user_id'] + """ !</b>  Your account has been approved successfully, Here is the link """ + self.sp_link + """ to Access Codex
                  </p>

                </div>

                </div>

                </body>
                </html>
                
                """


                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.email, self.password)
                server.sendmail(self.email, email, message.as_string())
                return {"status": "True"}
            else:
                return {"msg": "invalid email", "status": "False"}
        except Exception as e:
            generate_log('verify', str(e), str(request))
            return {"msg": "invalid email", "status": "False"}

    @jwt_required
    def changepassword(self, request):
        try:
            data = json.loads(request.data.decode())
            userid = get_jwt_identity()
            record = self.mongoObj.ReadValue("users", userid)
            record = ast.literal_eval(record["Data"])
            if (record['password'] == data["oldpassword"]):
                record['password'] = data["newpassword"]
                self.mongoObj.UpdateValue("users", userid,record)
                return {"status": "True"}
            else:
                return {"msg":"invalid old password","status":"False"}
        except Exception as e:
            generate_log('changepassword', str(e), str(request))

    def sendforgetemail(self, request):
        try:
            data = json.loads(request.data.decode())
            email = data["email"]
            record = self.mongoObj.ReadValue("users", email)
            if (record != None):
                message = Message(From=self.email,
                                  To=email)
                message.Subject = "Change Password"
                # message.Html = """<p>Hi!<br>
                #                                            Welcome to Stock Prediction<br>
                #                                            Here is the link """+ self.forgot_passwordLink + (str(base64.b64encode(bytes(email, "utf-8")).decode("utf-8"))).replace("=","~") + """  to change your password"""

                message.Html = """

                <!DOCTYPE html>
                <html>
                <head>
                <style>
               

                body{

                font-family: sans-serif;
                }

                .main{

                background-color : #f3f7fa;
                height:300px;
                padding: 25px 250px;

                }
                .main h1{

                color : #0070c9;
                text-align: center;

                }
                .sub-main{

                padding: 25px 50px;
                background-color:#FFF;

                }

                .main .sub-main h1{
                    text-align: center;
                    color : #46555d;
                    font-weight:200;
                }
                .main .sub-main p{

                    text-align: center;
                    color:#46555d;
                    font-size:14px;

                }
                .main .sub-main img{

                    display:block; margin-left:auto;margin-right:auto;width:10%;height:10%;
                }
                </style>
                </head>
                <body>


                <div class="main" style=" background-color : #f3f7fa;height:300px;padding: 25px 250px;">

                <h1 style="color : #0070c9;text-align: center;>Codex</h1>

                <div class="sub-main" style="padding: 25px 50px;background-color:#FFF;">

                    <img style="display:block; margin-left:auto;margin-right:auto;width:10%;height:10%;"  src='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRqbCA0f04h_Z2mbp3qs4Yr_Zxz5Xu_l8NYUCwOJMIJK7RWWGYW' />
                    <h1 style="text-align: center;color : #46555d;font-weight:200;">Reset Your Codex Password</h1>
                    <hr>
                     <p style=" text-align: center;color:#46555d;font-size:14px;">If this request is not from you, you can ignore this message and your account will still be secure.</p>
                      <p>Here is the link : <br>""" + self.forgot_passwordLink + (
                    str(base64.b64encode(bytes(email, "utf-8")).decode("utf-8"))).replace("=", "~") + """  to change your password
                   </p>

                </div>
                </div>


                </body>
                </html>
                """

                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.email, self.password)
                server.sendmail(self.email, email, message.as_string())
                return {"status": "True"}
            else:
                return {"msg":"invalid email","status":"False"}

        except Exception as e:
            generate_log('sendforgetemail', str(e), str(request))

    def forgot(self, request):
        try:
            data = json.loads(request.data.decode())
            email = base64.b64decode((bytes(str(data["email"]).replace("~","="),"utf-8"))).decode("utf-8")
            record = self.mongoObj.ReadValue("users", email)
            if (record != None):
                record = ast.literal_eval(record["Data"])
                record['password'] = data["newpassword"]
                self.mongoObj.UpdateValue("users", email, record)
                return {"status": "True"}
            else:
                return {"msg": "invalid email", "status": "False"}
        except Exception as e:
            generate_log('forgot', str(e), str(request))
            return {"msg": "invalid email", "status": "False"}

    # to show files names that have been uploaded by the user!
    @jwt_required
    def datainfo(self, request):
        userid = get_jwt_identity()
        try:
            record = self.mongoObj.ReadValue("datainfo", userid)
            record = ast.literal_eval(record["Data"])
            list = []
            for k, v in record.items():
                dic = v
                dic['filename'] = k
                list.append(dic)
            return list
        except Exception as e:
            generate_log('datainfo', str(e), str(request))
            return []

    def get_user_profile(self,request):
        try:
            data = json.loads(request.data.decode())
            userid = data['userid']
            record = self.mongoObj.ReadValue('users',userid)
            record = ast.literal_eval(record['Data'])
            record.pop('password')
            record.pop('status')
            return record
        except Exception as e:
            generate_log('get_user_profile', str(e), str(request))
            return {"msg": "invalid User", "status": "False"}

    # for contact us page (feedback email)
    def send_contact_email(self, request):
        try:
            data = json.loads(request.data.decode())
            first_name = data["first_name"]
            last_name = data["last_name"]
            email = data["email"]
            content = data["content"]
            if re.search(r'[\w.-]+@[\w.-]+.\w+', email):
                message = Message(From=self.email, To="Support-Codex-Contact")
                message.Subject = "Feedback " + first_name
                message.Html = """<p>Stock Prediction!<br>"""+\
                """<br>"""+"Name : "+first_name +" "+last_name+"""<br>"""+ \
                """<br>""" + "Email : " + email + """<br><br><br> """ + \
                               content
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.email, self.password)
                server.sendmail(self.email, self.email, message.as_string())
                return {"status": "True"}
            else:
                return {"msg": "invalid email", "status": "False"}
        except Exception as e:
            generate_log('get_user_profile', str(e), str(request))

    def twstest(self,request):
        try:
            data = json.loads(request.data.decode())
            ip = data["ip"]
            ClientID = data["ClientID"]
            Port = data["Port"]
            TestApp(ip, Port,ClientID)

        except Exception as e:
            generate_log('get_user_profile',str(e),str(request))















