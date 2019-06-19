from Depend import *
from user import user

class userApi(Resource):
    def __init__(self):
        self.name = "usersApi"
        self.user = user()

    def post(self):
        data = json.loads(request.data.decode())
        action = data["action"]

        if action == 'register':
            return self.user.register(request)

        elif action == 'update':
            return self.user.update(request)

        elif action == 'verify':
            return self.user.verify(request)

        elif action == 'changepassword':
            return self.user.changepassword(request)

        elif action == 'sendforgetemail':
            return self.user.sendforgetemail(request)

        elif action == 'forgetpassword':
            return self.user.forgot(request)

        elif action == 'getprofile':
            return self.user.get_user_profile(request)

        elif action == 'contactemail':
            return self.user.send_contact_email(request)

        elif action == 'datainfo':
            return self.user.datainfo(request)

        elif action == 'history':
            return self.user.history(request)
        elif action == "twstest":
            return self.user.twstest(request)

        # elif action == 'testTws':
        #     return self.user.twstest(request)
