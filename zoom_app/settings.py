from os import environ

CLIENT_ID = environ.get('CLIENT_ID')
CLIENT_SECRET = environ.get('CLIENT_SECRET')
AUTHORIZATION_BASE_URL = environ.get('AUTHORIZATION_BASE_URL')
TOKEN_URL = environ.get('TOKEN_URL')
REDIRECT_URI = environ.get('REDIRECT_URI')
REFRESH_URL = TOKEN_URL