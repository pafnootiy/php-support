from django.urls import path

from .views import *

urlpatterns = [
    path('', index, name='index'),
    path('add_developer/', add_developer, name='add_developer'),
    path('manage_developers/', manage_developers, name='manage_developers')
    # path('test/',test),
]
