import os

import shortuuid
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils._os import safe_join

from core.exceptions import BadRequest, InternalServerError


class ImageUpload:
    @staticmethod
    def verify_image(image: InMemoryUploadedFile):
        if image.size > 10 * 1024 * 1024:  # 10MB
            raise BadRequest("Image is too large")

        if image.size < 10 * 1024:  # 10KB
            raise BadRequest("Image is too small")

        if image.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise BadRequest("Invalid image extension")

    @staticmethod
    def upload_image_and_get_url(image: InMemoryUploadedFile):
        ImageUpload.verify_image(image)
        image.file.seek(0)
        try:
            extension = os.path.splitext(image.name)[1].lstrip(".")
            filename = f"{shortuuid.uuid()}.{extension}"
            relative_dir = settings.IMAGE_UPLOAD_FOLDER.strip("/")
            relative_path = os.path.join(relative_dir, filename)
            destination_dir = safe_join(settings.MEDIA_ROOT, relative_dir)
            os.makedirs(destination_dir, exist_ok=True)
            destination_path = safe_join(destination_dir, filename)
            with open(destination_path, "wb") as out_file:
                out_file.write(image.file.read())
            public_base = settings.PUBLIC_BASE_URL.rstrip("/") if settings.PUBLIC_BASE_URL else ""
            if public_base:
                return f"{public_base}{settings.MEDIA_URL}{relative_path}"
            return f"{settings.MEDIA_URL}{relative_path}"
        except Exception as e:
            print(e)
            raise InternalServerError("Failed to upload image")
