from django.urls import path,include
from .import views
urlpatterns = [
path('document/',views.DocumentAddView.as_view()),
path('document-Add/',views.DocumentAddView.as_view()), 
path('document/<int:id>/',views.DocumentDetailView.as_view()) ,
path('document-update/<int:id>/',views.DocumentUpdateView.as_view()), 
path('document-Delete/<int:id>/',views.DocumentDeleteView.as_view()),
path('upload/',views.UploadToGoogleDrive.as_view(), name='upload_to_google_drive') ,
path('drive/list/', views.GoogleDriveOAuthView.as_view(), name='list_drive_files'),

]