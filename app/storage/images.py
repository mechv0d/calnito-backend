from io import BytesIO
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings


@dataclass(frozen=True)
class ProcessedImage:
    bytes: bytes
    width: int
    height: int
    content_type: str = 'image/webp'


class ImageProcessingError(ValueError):
    pass


def process_food_photo(raw_bytes: bytes) -> ProcessedImage:
    settings = get_settings()

    try:
        image = Image.open(BytesIO(raw_bytes))
    except UnidentifiedImageError as exc:
        raise ImageProcessingError('Invalid image file') from exc

    image = ImageOps.exif_transpose(image)
    image = image.convert('RGB')

    width, height = image.size
    max_side = max(width, height)
    if max_side > settings.max_image_side_px:
        scale = settings.max_image_side_px / max_side
        image = image.resize(
            (round(width * scale), round(height * scale)),
            Image.Resampling.LANCZOS,
        )

    output = BytesIO()
    # Создание нового RGB + сохранение без EXIF/ICC фактически чистит метаданные.
    image.save(
        output,
        format='WEBP',
        quality=settings.webp_quality,
        method=6,
        exif=b'',
        icc_profile=None,
    )

    final_width, final_height = image.size
    return ProcessedImage(bytes=output.getvalue(), width=final_width, height=final_height)
