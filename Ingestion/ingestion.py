from Ingestion.chunking import create_semantic_chunks, process_images_with_caption, process_tables_with_description
from Ingestion.helper import get_embeddings, get_opensearch_client


def create_index_if_not_exists(client, index_name):
    """Check if the index exists in OpenSearch, and create it if it doesn't."""
    if client.indices.exists(index=index_name):
        print(f"Index '{index_name}' already exists.")
        client.indices.delete(index=index_name)

    body = {
        "mappings": {
            "properties": {
                "content": {"type": "text"},
                "content_type": {"type": "keyword"},
                "filename": {"type": "keyword"},
                "embedding": {"type": "knn_vector", "dimension": 768},
            }
        },
        "settings": {
            "index": {
                "knn": True,
                "knn.space_type": "cosinesimil",
            }
        },
    }
    try:
        client.indices.create(index=index_name, body=body)
        print(f"Index '{index_name}' created successfully.")
    except Exception as e:
        print(f"Error creating index '{index_name}': {e}")
        raise


def prepare_chunks_for_ingestion(chunks):
    """Prepare the processed chunks for ingestion into OpenSearch."""
    prepared_chunks = []
    for idx, chunk in enumerate(chunks):
        if not chunk.get("content"):
            print(f"Skipping chunk {idx} due to missing content.")
            continue

        try:
            embedding = get_embeddings(chunk["content"])
        except Exception as e:
            print(f"Skipping chunk {idx} due to embedding error: {e}")
            continue
        if not embedding:
            print(f"Skipping chunk {idx} due to missing embedding.")
            continue

        chunk_data = {
            "content": chunk.get("content", ""),
            "content_type": chunk.get("content_type", "text"),
            "filename": chunk.get("filename", None),
            "embedding": embedding,
        }
        prepared_chunks.append(chunk_data)

    return prepared_chunks


def ingest_chunks_into_opensearch(client, index_name, chunks):
    """Ingest a list of prepared chunks into OpenSearch."""
    for idx, chunk in enumerate(chunks):
        client.index(index=index_name, body=chunk)
    print(f"Ingested {len(chunks)} chunks into '{index_name}'.")


def ingest_all_content_into_opensearch(processed_images, processed_tables, semantic_chunks, index_name):
    """Ingest all processed content (images, tables, text) into OpenSearch."""
    client = get_opensearch_client("localhost", 9200)

    create_index_if_not_exists(client, index_name)

    images_chunks = prepare_chunks_for_ingestion(processed_images)
    ingest_chunks_into_opensearch(client, index_name, images_chunks)

    tables_chunks = prepare_chunks_for_ingestion(processed_tables)
    ingest_chunks_into_opensearch(client, index_name, tables_chunks)

    semantic_chunks = prepare_chunks_for_ingestion(semantic_chunks)
    ingest_chunks_into_opensearch(client, index_name, semantic_chunks)


if __name__ == "__main__":
    from unstructured.partition.pdf import partition_pdf

    pdf_file_path = "C:\\Users\\amitg\\Desktop\\RAG-rp\\paper\\RAG-paper.pdf"
    raw_chunks = partition_pdf(
        filename=pdf_file_path,
        strategy="hi_res",
        infer_table_structure=True,
        extract_image_block_types=["figure", "Image", "Table"],
        extract_image_block_to_payload=True,
        chunking_strategy=None,
    )
    processed_images = process_images_with_caption(raw_chunks, use_openai=True)
    processed_tables = process_tables_with_description(raw_chunks, use_openai=True)

    text_chunks = partition_pdf(
        filename=pdf_file_path,
        strategy="hi_res",
        max_characters=2000,
        combine_text_under_n_chars=500,
        new_after_n_chars=1500,
        chunking_strategy="by_title",
    )

    semantic_chunks = create_semantic_chunks(text_chunks)

    index_name = "research_paper_index"
    ingest_all_content_into_opensearch(processed_images, processed_tables, semantic_chunks, index_name)
