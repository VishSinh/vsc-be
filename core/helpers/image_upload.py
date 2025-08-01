import os

import boto3
import shortuuid
from botocore.config import Config
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

from core.exceptions import BadRequest, InternalServerError


class ImageUpload:
    client = boto3.client(
        "s3",
        region_name=settings.S3_CLIENT_REGION,
        endpoint_url=settings.S3_CLIENT_ENDPOINT,
        aws_access_key_id=settings.S3_CLIENT_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_CLIENT_SECRET_ACCESS_KEY,
        config=Config(s3={"addressing_style": "path"}),
    )

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

        image.file.seek(0)  # Reset file pointer to beginning,

        try:
            extension = os.path.splitext(image.name)[1].lstrip(".")
            object_key = f"{settings.S3_IMAGE_FOLDER}/{shortuuid.uuid()}.{extension}"

            ImageUpload.client.put_object(
                Bucket=settings.BUCKET_NAME,
                Key=object_key,
                Body=image.file,
                ContentType=image.content_type,
            )

            return f"{settings.S3_DOWNLOAD_URL}/{object_key}"
        except Exception:
            raise InternalServerError("Failed to upload image")
