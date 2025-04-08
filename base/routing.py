from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/study_group/(?P<group_id>\d+)/$', consumers.StudyGroupConsumer.as_asgi()),
]
