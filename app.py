from flask import Flask

app = Flask(__name__)

import controller_article
import controller_auth
import controller_ml_model

if __name__ == "__main__":
    app.run()
