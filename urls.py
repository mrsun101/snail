from snail.urls import Url
from views import Homepage, EpicMath, Hello


urlpatterns = [
    Url('^$', Homepage),
    Url('^/math$', EpicMath),
    Url('^/hello$', Hello)
]