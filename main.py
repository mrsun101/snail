import os
from snail.main import Snail
from urls import urlpatterns
from snail.middleware import middlewares

settings = {
    'BASE_DIR': os.path.dirname(os.path.abspath(__file__)),
    'TEMPLATES_DIR_NAME': 'templates'
}

app = Snail(
    urls=urlpatterns, settings=settings, middlewares=middlewares
)