from ddtrace import patch_all
patch_all()

from flask import Flask
import logging

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

import web.routes
