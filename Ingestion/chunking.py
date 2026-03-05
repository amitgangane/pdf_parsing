import os
import base64
from dotenv import load_dotenv
from openai import OpenAI
from unstructured.documents.elements import FigureCaption, Image, Table

load_dotenv()


def generate_caption(client, image_data):
    prompt = (
        f"You are an assistant that generates a detailed description. the caption is: {image_data['caption']}."
        f"The image text is: {image_data['image_text']}."
        f"The description should be concise and descriptive, highlighting the main elements of the image."
        f"do not use any extraneous information that is not present in the image or the caption."
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data['base64_image']}"}},
                ],
            }
        ],
        max_tokens=300,
    )
    return response.choices[0].message.content


def process_images_with_caption(raw_chunks, use_openai=True):
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    client = OpenAI(api_key=api_key) if use_openai else None

    all_image = []

    for idx, chunk in enumerate(raw_chunks):
        if isinstance(chunk, Image):
            if idx + 1 < len(raw_chunks) and isinstance(raw_chunks[idx + 1], FigureCaption):
                caption = raw_chunks[idx + 1].text
            else:
                caption = None

            image_data = {
                "caption": caption,
                "image_text": chunk.text,
                "base64_image": chunk.metadata.image_base64,
                "content": chunk.text,  # fallback to text content if image captioning fails
                "content_type": "image",
                "filename": chunk.metadata.filename,
            }

            if use_openai:
                image_data["content"] = generate_caption(client, image_data)

            all_image.append(image_data)

    return all_image


def process_tables_with_description(raw_chunks, use_openai=True):
    
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")
    client = OpenAI(api_key=api_key) if use_openai else None

    # now we will handle tables
    all_tables = []
    for idx, element in enumerate(raw_chunks):
        if isinstance(element, Table):
            table_item = {
                "table_as_html": element.metadata.text_as_html,
                "table_text": element.text,
                "content": element.text,  # fallback to text content if table description generation fails
                "content_type": "table",
                "filename": element.metadata.filename,
            }
            if use_openai:
                prompt = (
                    f"You are an assistant that generates a detailed description of the table. "
                    f"The table is represented in HTML format: {table_item['table_as_html']}."
                    f"Generate a concise and informative description of the table, highlighting key insights and trends."
                    f"Focus on the main elements of the table, such as headers, rows, and any notable patterns or outliers."
                )
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    max_tokens=300,
                )
                table_item["content"] = response.choices[0].message.content
            all_tables.append(table_item)

    return all_tables


def create_semantic_chunks(raw_chunks):
    from unstructured.documents.elements import CompositeElement
    processed_chunks = []
    for idx, chunk in enumerate(raw_chunks):
        if isinstance(chunk, CompositeElement):
            chunk_data = {
                "content": chunk.text,
                "content_type": "text",
                "filename": chunk.metadata.filename if chunk.metadata else None,
            }
            processed_chunks.append(chunk_data)
    return processed_chunks

