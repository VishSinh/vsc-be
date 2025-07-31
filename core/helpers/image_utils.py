import imagehash
import shortuuid
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image

from core.exceptions import InternalServerError


class ImageUtils:
    @staticmethod
    def generate_perceptual_hash(image: InMemoryUploadedFile) -> str:
        try:
            image.file.seek(0)  # Reset file pointer to beginning
            pil_image = Image.open(image.file)
            hash_value = imagehash.average_hash(pil_image)
            return str(hash_value)
        except Exception:
            raise InternalServerError("Failed to generate perceptual hash")

    @staticmethod
    def generate_unique_barcode(model_class=None):
        max_attempts = 10
        for _ in range(max_attempts):
            barcode = shortuuid.uuid()[:10]

            if model_class and hasattr(model_class, "objects"):
                if not model_class.objects.filter(barcode=barcode).exists():
                    return barcode
            else:
                return barcode

        raise InternalServerError("Unable to generate unique barcode after multiple attempts")
