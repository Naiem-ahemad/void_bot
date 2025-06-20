import requests
import os
import uuid
from config import IMAGE_FOLDER

os.makedirs(IMAGE_FOLDER, exist_ok=True)

def generate_image(prompt):
    safe_prompt = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}"
    response = requests.get(url)

    filename = f"{uuid.uuid4()}.jpg"
    img_path = os.path.join(IMAGE_FOLDER, filename)

    with open(img_path, "wb") as f:
        f.write(response.content)

    return img_path
