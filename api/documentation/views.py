from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Document
from rest_framework import status
from .serializers import DocumentSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from googleapiclient.http import MediaFileUpload
from .google_auth import get_drive_service
from django.http import JsonResponse
from django.views import View
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os
import pickle
from django.conf import settings

# Create your views here.
class DocumentAddView (APIView):
    def post(self, request, *args, **kwargs):
        serializer = DocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class DocumentView (APIView):
    def get(self, request, *args, **kwargs):
        documents = Document.objects.all()
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)
class DocumentDetailView (APIView):
     def get(self, request, *args, **kwargs):
        id = kwargs.get('id')
        document = Document.objects.get(id=id)
        serializer = DocumentSerializer(document)
        return Response(serializer.data)
class DocumentUpdateView (APIView):
            def put(self, request, *args, **kwargs):
                id = kwargs.get('id')
                document = Document.objects.get(id=id)
                serializer = DocumentSerializer(document, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            def patch(self, request, *args, **kwargs):
                id = kwargs.get('id')
                document = Document.objects.get(id=id)
                serializer = DocumentSerializer(document, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class DocumentDeleteView (APIView):
            def delete(self, request, *args, **kwargs):
                id = kwargs.get('id')
                document = Document.objects.get(id=id)
                document.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)

class UploadToGoogleDrive(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES['file']
        file_path = f"tmp/{file_obj.name}"
        
        with open(file_path, 'wb+') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)

        service = get_drive_service()

        file_metadata = {"name": file_obj.name, "parents": ["VOTRE_DOSSIER_ID"]}
        media = MediaFileUpload(file_path, mimetype=file_obj.content_type)

        file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        
        os.remove(file_path)

        return Response({"file_id": file.get("id")})
    


SCOPES = ['https://www.googleapis.com/auth/drive.file']
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request
# from googleapiclient.discovery import build
# from django.conf import settings
# from django.shortcuts import render
# from django.views import View

# class GoogleDriveFileListView(View):
#     def get(self, request):
#         creds = None
#         # Token file is used to store the user's access and refresh tokens
#         if os.path.exists('token.json'):
#             creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive.readonly'])
        
#         # If there are no valid credentials available, let the user log in
#         if not creds or not creds.valid:
#             if creds and creds.expired and creds.refresh_token:
#                 creds.refresh(Request())
#             else:
#                 flow = InstalledAppFlow.from_client_secrets_file(
#                     settings.GOOGLE_OAUTH2_CREDENTIALS_JSON,
#                     ['https://www.googleapis.com/auth/drive.readonly']
#                 )
#                 creds = flow.run_local_server(port=0)
            
#             # Save the credentials for the next run
#             with open('token.json', 'w') as token:
#                 token.write(creds.to_json())

#         try:
#             # Build the Drive API client
#             service = build('drive', 'v3', credentials=creds)

#             # Request to list the files in Google Drive
#             results = service.files().list(
#                 pageSize=10,  # Number of files to retrieve per request
#                 fields="files(id, name)"
#             ).execute()
            
#             files = results.get('files', [])

#             if not files:
#                 return render(request, 'error.html', {'message': 'No files found.'})
            
#             return render(request, 'file_list.html', {'files': files})

#         except Exception as error:
#             return render(request, 'error.html', {'message': f'An error occurred: {error}'})
# import os
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request
# from googleapiclient.discovery import build
# from django.conf import settings
# from django.shortcuts import render
# from django.views import View

# class GoogleDriveOAuthView(View):
#     def get(self, request):
#         creds = None
        
#         # If token exists, use it for authentication (already authorized)
#         if os.path.exists('token.json'):
#             creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive.readonly'])
        
#         # If no valid credentials, run OAuth flow to authenticate
#         if not creds or not creds.valid:
#             if creds and creds.expired and creds.refresh_token:
#                 creds.refresh(Request())
#             else:
#                 flow = InstalledAppFlow.from_client_secrets_file(
#                     settings.GOOGLE_OAUTH2_CREDENTIALS_JSON,
#                     ['https://www.googleapis.com/auth/drive.readonly']
#                 )
#                 creds = flow.run_local_server(port=0)  # This will launch a local server for authentication
                
#             # Save the credentials for future use
#             with open('token.json', 'w') as token:
#                 token.write(creds.to_json())

#         # Now you can use the `creds` to make API requests to Google Drive
#         service = build('drive', 'v3', credentials=creds)
#         # Example: List files from Google Drive
#         results = service.files().list(pageSize=10, fields="files(id, name)").execute()
#         files = results.get('files', [])

#         return render(request, 'google_drive_list.html', {'files': files})
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from django.conf import settings
from django.shortcuts import redirect, render
from django.views import View
from django.http import HttpResponse

class GoogleDriveOAuthView(View):
    def get(self, request):
        creds = None
        
        # If token exists, use it for authentication (already authorized)
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive.readonly'])
        
        # If no valid credentials, run OAuth flow to authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Step 1: Generate the authorization URL
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.GOOGLE_OAUTH2_CREDENTIALS_JSON,
                    ['https://www.googleapis.com/auth/drive.readonly']
                )

                # Generate the authorization URL
                auth_url, state = flow.authorization_url(
                    access_type='offline',  # Allow offline access to refresh tokens
                    include_granted_scopes='true'  # Request incremental authorization
                )
                
                # Store the state in the session to verify during the callback
                request.session['state'] = state

                # Step 2: Redirect user to Google's OAuth 2.0 server
                return redirect(auth_url)
        
        # After the OAuth flow is completed, list Google Drive files
        service = build('drive', 'v3', credentials=creds)
        results = service.files().list(pageSize=10, fields="files(id, name)").execute()
        files = results.get('files', [])

        return render(request, 'google_drive_list.html', {'files': files})

class GoogleDriveCallbackView(View):
    def get(self, request):
        # Get the state stored in the session during the initial authorization step
        state = request.session.get('state')

        # Create the flow object from the client secrets
        flow = InstalledAppFlow.from_client_secrets_file(
            settings.GOOGLE_OAUTH2_CREDENTIALS_JSON,
            ['https://www.googleapis.com/auth/drive.readonly']
        )
        
        # Step 3: The user has authorized, now exchange the code for a token
        flow.fetch_token(
            authorization_response=request.build_absolute_uri(),
            state=state
        )

        creds = flow.credentials
        
        # Save credentials for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

        # Use credentials to interact with the Google API
        service = build('drive', 'v3', credentials=creds)
        results = service.files().list(pageSize=10, fields="files(id, name)").execute()
        files = results.get('files', [])

        return render(request, 'google_drive_list.html', {'files': files})
