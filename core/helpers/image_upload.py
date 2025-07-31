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

    def verify_image(self, image: InMemoryUploadedFile):
        if image.size > 10 * 1024 * 1024:
            raise BadRequest("Image is too large")

        if image.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise BadRequest("Invalid image extension")

    def upload_image(self, image: InMemoryUploadedFile):
        self.verify_image(image)

        try:
            extension = os.path.splitext(image.name)[1].lstrip(".")

            object_key = f"{settings.S3_IMAGE_FOLDER}/{shortuuid.uuid()}.{extension}"

            self.client.put_object(
                Bucket=settings.BUCKET_NAME,
                Key=object_key,
                Body=image.file,
                ContentType=image.content_type,
            )

            print("Image uploaded to S3")

            return f"{settings.S3_DOWNLOAD_URL}/{object_key}"
        except Exception:
            raise InternalServerError("Failed to upload image")
