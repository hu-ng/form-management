from zoom_app import app
import os

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"  # Allow calls through http, change in production
    app.run(debug=True)