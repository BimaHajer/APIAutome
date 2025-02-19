from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from io import BytesIO
import os
import json
import logging

logger = logging.getLogger(__name__)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

class GoogleDriveAuth:
    """Helper class for Google Drive authentication"""
    
    @staticmethod
    def get_credentials(request):
        if 'credentials' not in request.session:
            return None
            
        try:
            creds_info = json.loads(request.session['credentials'])
            creds = Credentials.from_authorized_user_info(creds_info)
            
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    request.session['credentials'] = creds.to_json()
                else:
                    return None
                    
            return creds
        except Exception as e:
            logger.error(f"Error getting credentials: {str(e)}")
            return None

    @staticmethod
    def get_service(credentials):
        return build('drive', 'v3', credentials=credentials)

class DriveAuthView(View):
    """Handle Google Drive OAuth flow"""
    
    def get(self, request):
        flow = Flow.from_client_secrets_file(
            settings.GOOGLE_CLIENT_SECRET_FILE,
            scopes=settings.GOOGLE_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        request.session['state'] = state
        return redirect(authorization_url)

class DriveCallbackView(View):
    """Handle OAuth callback"""
    
    def get(self, request):
        if 'state' not in request.session:
            return redirect('/drive/auth/')
        
        try:
            state = request.session['state']
            flow = Flow.from_client_secrets_file(
                settings.GOOGLE_CLIENT_SECRET_FILE,
                scopes=settings.GOOGLE_SCOPES,
                state=state,
                redirect_uri=settings.GOOGLE_REDIRECT_URI
            )
            flow.fetch_token(authorization_response=request.build_absolute_uri())
            credentials = flow.credentials
            request.session['credentials'] = credentials.to_json()
            return redirect('/drive/list/')
            
        except Exception as e:
            logger.error(f"Callback error: {str(e)}")
            return redirect('/drive/auth/')
class BaseGoogleDriveView(View):
    """Base class for Google Drive views"""
    
    def dispatch(self, request, *args, **kwargs):
        self.credentials = GoogleDriveAuth.get_credentials(request)
        if not self.credentials:
            return redirect('/drive/auth/')
        
        try:
            service = build('oauth2', 'v2', credentials=self.credentials)
            user_info = service.userinfo().get().execute()
            self.user_email = user_info.get('email')
        except Exception as e:
            logger.error(f"Error getting user email: {str(e)}")
            self.user_email = None
            
        return super().dispatch(request, *args, **kwargs)

@method_decorator(csrf_exempt, name='dispatch')
class DriveListFilesView(BaseGoogleDriveView):
    """Handle listing files"""
    
    def get(self, request):
        try:
            service = GoogleDriveAuth.get_service(self.credentials)
            query = f"'me' in owners or '{self.user_email}' in writers"
            results = service.files().list(
                pageSize=10,
                fields="files(id, name, mimeType, createdTime, owners, shared)",
                q=query
            ).execute()
            
            files = results.get('files', [])
            for file in files:
                file['user_email'] = self.user_email
                file['is_owner'] = any(owner.get('emailAddress') == self.user_email 
                                     for owner in file.get('owners', []))
            
            return JsonResponse({
                'files': files,
                'user_email': self.user_email
            })
            
        except Exception as e:
            logger.error(f"File listing error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class DriveFileDetailView(BaseGoogleDriveView):
    """Handle getting file details"""
    
    def get(self, request, file_id):
        try:
            service = GoogleDriveAuth.get_service(self.credentials)
            file = service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, createdTime, owners'
            ).execute()
            
            response_data = {
                **file,
                'user_email': self.user_email,
                'is_owner': any(owner.get('emailAddress') == self.user_email 
                              for owner in file.get('owners', []))
            }
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"File detail error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class DriveFileCreateView(BaseGoogleDriveView):
    """Handle file creation"""
    
    def post(self, request):
        try:
            service = GoogleDriveAuth.get_service(self.credentials)
            
            file_metadata = {
                'name': request.POST.get('name', 'Untitled'),
                'mimeType': request.POST.get('mimeType', 'application/vnd.google-apps.document')
            }
            
            share_with = request.POST.getlist('share_with', [])
            
            if 'file' in request.FILES:
                media = MediaFileUpload(
                    request.FILES['file'],
                    mimetype=request.FILES['file'].content_type,
                    resumable=True
                )
                file = service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
            else:
                file = service.files().create(
                    body=file_metadata,
                    fields='id'
                ).execute()
            
            for email in share_with:
                permission = {
                    'type': 'user',
                    'role': 'writer',
                    'emailAddress': email
                }
                service.permissions().create(
                    fileId=file.get('id'),
                    body=permission,
                    sendNotificationEmail=True
                ).execute()
            
            return JsonResponse({
                'message': 'File created successfully',
                'file_id': file.get('id'),
                'shared_with': share_with,
                'owner_email': self.user_email
            })
            
        except Exception as e:
            logger.error(f"File creation error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
@method_decorator(csrf_exempt, name='dispatch')
class DriveFileUpdateView(BaseGoogleDriveView):
    """Handle file updates"""
    
    def get(self, request, file_id):
        """Get file update form"""
        try:
            service = GoogleDriveAuth.get_service(self.credentials)
            file = service.files().get(
                fileId=file_id,
                fields='id, name, mimeType, createdTime, owners'
            ).execute()
            
            # Check ownership
            if not any(owner.get('emailAddress') == self.user_email 
                      for owner in file.get('owners', [])):
                return JsonResponse(
                    {'error': 'You do not have permission to modify this file'}, 
                    status=403
                )
            
            # Get current sharing settings
            permissions = service.permissions().list(
                fileId=file_id,
                fields='permissions(id,emailAddress,role)'
            ).execute()
            
            response_data = {
                **file,
                'user_email': self.user_email,
                'permissions': permissions.get('permissions', [])
            }
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"File update form error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def put(self, request, file_id):
        """Update file"""
        try:
            service = GoogleDriveAuth.get_service(self.credentials)
            data = json.loads(request.body)
            
            # Check ownership
            file = service.files().get(
                fileId=file_id, 
                fields='owners'
            ).execute()
            
            if not any(owner.get('emailAddress') == self.user_email 
                      for owner in file.get('owners', [])):
                return JsonResponse(
                    {'error': 'You do not have permission to modify this file'}, 
                    status=403
                )
            
            # Update file metadata
            file_metadata = {
                'name': data.get('name'),
                'description': data.get('description', '')
            }
            
            # Update sharing settings
            share_updates = data.get('share_updates', [])
            for update in share_updates:
                permission = {
                    'type': 'user',
                    'role': update.get('role', 'reader'),
                    'emailAddress': update.get('email')
                }
                service.permissions().create(
                    fileId=file_id,
                    body=permission,
                    sendNotificationEmail=True
                ).execute()
            
            # Remove permissions if specified
            remove_permissions = data.get('remove_permissions', [])
            for email in remove_permissions:
                # Find and delete permission by email
                permissions = service.permissions().list(
                    fileId=file_id,
                    fields='permissions(id,emailAddress)'
                ).execute()
                
                for perm in permissions.get('permissions', []):
                    if perm.get('emailAddress') == email:
                        service.permissions().delete(
                            fileId=file_id,
                            permissionId=perm['id']
                        ).execute()
            
            # Update file
            updated_file = service.files().update(
                fileId=file_id,
                body=file_metadata,
                fields='id, name, mimeType, createdTime, owners'
            ).execute()
            
            return JsonResponse({
                'message': 'File updated successfully',
                'file': updated_file,
                'owner_email': self.user_email
            })
            
        except Exception as e:
            logger.error(f"File update error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
@method_decorator(csrf_exempt, name='dispatch')
class DriveFileDeleteView(BaseGoogleDriveView):
    """Handle file deletion"""
    
    def delete(self, request, file_id):
        try:
            service = GoogleDriveAuth.get_service(self.credentials)
            
            file = service.files().get(
                fileId=file_id, 
                fields='owners'
            ).execute()
            
            if not any(owner.get('emailAddress') == self.user_email 
                      for owner in file.get('owners', [])):
                return JsonResponse(
                    {'error': 'You do not have permission to delete this file'}, 
                    status=403
                )
            
            service.files().delete(fileId=file_id).execute()
            return JsonResponse({
                'message': 'File deleted successfully',
                'owner_email': self.user_email
            })
            
        except Exception as e:
            logger.error(f"File deletion error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
class DriveDownloadView(View):
    """Handle file downloads"""
    
    def get(self, request, file_id):
        credentials = GoogleDriveAuth.get_credentials(request)
        if not credentials:
            return redirect('/drive/auth/')
            
        try:
            service = GoogleDriveAuth.get_service(credentials)
            
            # Get file metadata
            file = service.files().get(fileId=file_id).execute()
            file_name = file.get('name', 'downloaded_file')
            
            # Download file content
            request = service.files().get_media(fileId=file_id)
            fh = BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # Prepare response
            fh.seek(0)
            response = HttpResponse(fh.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            
            return response
            
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)