import string
import secrets
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO

def generate_security_code():
    letters = string.ascii_letters
    return ''.join(secrets.choice(letters) for _ in range(5))


def generate_captcha_pixmap(text):
    width, height = 180, 60
    image = Image.new("RGB", (width, height), (235, 242, 255))
    draw = ImageDraw.Draw(image)

    font = ImageFont.truetype("arialbd.ttf", 36)

    # Noise dots
    for _ in range(1000):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(random.randint(120, 200),)*3)

    # Draw characters
    x = 15
    for ch in text:
        y = random.randint(5, 15)
        draw.text((x, y), ch, font=font, fill=(0, 60, 160))
        x += random.randint(28, 34)

    # Curved noise lines
    for _ in range(2):
        draw.arc(
            [0, random.randint(10, 30), width, random.randint(40, 60)],
            start=0, end=360, fill=(100, 120, 200), width=2
        )

    image = image.filter(ImageFilter.GaussianBlur(1))

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
