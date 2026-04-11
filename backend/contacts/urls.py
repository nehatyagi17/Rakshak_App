from django.urls import path
from .views import ContactListView, ContactAddView, ContactRemoveView

urlpatterns = [
    path('', ContactListView.as_view(), name='contact_list'),
    path('add/', ContactAddView.as_view(), name='contact_add'),
    path('<str:contact_id>/remove/', ContactRemoveView.as_view(), name='contact_remove'),
]
