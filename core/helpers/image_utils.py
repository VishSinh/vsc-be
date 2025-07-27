from io import BytesIO

import imagehash
import requests  # type: ignore
from PIL import Image

from core.exceptions import InternalServerError


class ImageUtils:
    """Utility functions for image processing operations"""

    @staticmethod
    def generate_perceptual_hash(image_url: str) -> str:
        """
        Generate a perceptual hash for an image from URL.

        Args:
            image_url (str): URL of the image to hash

        Returns:
            str: Perceptual hash string

        Raises:
            InternalServerError: If image processing fails
        """
        try:
            response = requests.get(image_url)
            response.raise_for_status()  # Raise exception for bad status codes

            image = Image.open(BytesIO(response.content))
            hash_value = imagehash.average_hash(image)
            return str(hash_value)
        except Exception as e:
            raise InternalServerError(f"Failed to generate perceptual hash: {str(e)}")

    @staticmethod
    def generate_unique_barcode(prefix: str = "CARD", model_class=None) -> str:
        """
        Generate a unique barcode with timestamp and random suffix.

        Args:
            prefix (str): Prefix for the barcode (default: "CARD")
            model_class: Django model class to check uniqueness against

        Returns:
            str: Unique barcode string

        Raises:
            InternalServerError: If unable to generate unique barcode
        """
        import time
        import uuid

        max_attempts = 10
        for _ in range(max_attempts):
            timestamp = int(time.time() * 1000)
            random_suffix = str(uuid.uuid4())[:8]
            barcode = f"{prefix}_{timestamp}_{random_suffix}"

            # Check uniqueness if model_class is provided
            if model_class and hasattr(model_class, "objects"):
                if not model_class.objects.filter(barcode=barcode).exists():
                    return barcode
            else:
                return barcode  # Return without checking if no model provided

        raise InternalServerError("Unable to generate unique barcode after multiple attempts")
