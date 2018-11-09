import os
import uuid

from django.core.exceptions import PermissionDenied

from . import conf
from .ajaxuploader.backends.local import LocalUploadBackend
from .ajaxuploader.views import AjaxFileUploader
from .models import UploadedFile
from .util import load_class
from django_file_form.ajaxuploader.backends.base import AbstractUploadBackend
from .models import get_storage


class FileFormUploadBackend(LocalUploadBackend):
    UPLOAD_DIR = conf.UPLOAD_DIR

    def upload_complete(self, request, filename, file_id, *args, **kwargs):
        result = super(FileFormUploadBackend, self).upload_complete(
            request, filename, file_id, *args, **kwargs)

        # get the filename if only resized image is uploaded
        if request.POST.get('qqfilename'):
            original_filename = request.POST['qqfilename']
        else:
            original_filename = request.FILES['qqfile'].name

        values = dict(
            uploaded_file=os.path.join(self.UPLOAD_DIR, filename),
            file_id=file_id,
            form_id=request.POST['form_id'],
            original_filename=original_filename,
        )

        field_name = request.POST.get('field_name')
        if field_name:
            values['field_name'] = field_name

        UploadedFile.objects.create(**values)

        return result

    def update_filename(self, request, filename, *args, **kwargs):
        return uuid.uuid4().hex


class FileFormUploader(AjaxFileUploader):
    def __init__(self, backend=None, **kwargs):
        if not backend:
            backend = load_class('UPLOAD_BACKEND')
        super(FileFormUploader, self).__init__(backend, **kwargs)

    def __call__(self, request, *args, **kwargs):
        if conf.MUST_LOGIN and not request.user.is_authenticated():
            raise PermissionDenied()

        return super(FileFormUploader, self).__call__(request, *args, **kwargs)


class RemoteUploadBackend(AbstractUploadBackend):
    storage_object = None
    UPLOAD_DIR=conf.UPLOAD_DIR

    def setup(self, filename, *args, **kwargs):
        self.setup_storage()
        self._path = self.get_path(filename, *args, **kwargs)
        self._dest = self.storage_object.open(self._path, "w")

    def setup_storage(self):
        if not self.storage_object:
            self.storage_object = get_storage()

    def get_path(self, filename, *args, **kwargs):
        return os.path.join(self.UPLOAD_DIR, filename)

    def upload_chunk(self, chunk, *args, **kwargs):
        self._dest.write(chunk)

    def upload_complete(self, request, filename, file_id, *args, **kwargs):
        result = self.upload_complete_aux(filename)

        # get the filename if only resized image is uploaded
        if request.POST.get('qqfilename'):
            original_filename = request.POST['qqfilename']
        else:
            original_filename = request.FILES['qqfile'].name

        values = dict(
            uploaded_file=os.path.join(self.UPLOAD_DIR, filename),
            file_id=file_id,
            form_id=request.POST['form_id'],
            original_filename=original_filename,
        )

        field_name = request.POST.get('field_name')
        if field_name:
            values['field_name'] = field_name

        UploadedFile.objects.create(**values)

        return result

    def upload_complete_aux(self, filename):
        path = self.UPLOAD_DIR + "/" + filename
        self._dest.close()
        return {"path": path}

    def update_filename(self, request, filename, *args, **kwargs):
        return uuid.uuid4().hex

    def delete(self, uploaded_file):
        self.setup_storage()
        self.storage_object.delete(uploaded_file.name)