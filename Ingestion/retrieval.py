from Ingestion.helper import get_embeddings, get_opensearch_client

INDEX_NAME = "research_paper_index"


def keyword_search(query_text, top_k=20):
    """
    Perform keyword search using OpenSearch.

    Args:
        query_text (str): The query text to search for
        top_k (int): Number of results to return

    Returns:
        list: Search results
    """
    client = get_opensearch_client("localhost", 9200)

    try:
        # Create a keyword search query
        search_query = {
            "size": top_k,
            "query": {"match": {"content": query_text}},
            "_source": ["content", "content_type", "filename"],
        }

        response = client.search(index=INDEX_NAME, body=search_query)
        return response["hits"]["hits"]
    except Exception as e:
        print(f"Keyword search error: {e}")
        return []


def semantic_search(query_text, top_k=20):
    """
    Perform semantic search using vector embeddings.

    Args:
        query_text (str): The query text to search for
        top_k (int): Number of results to return

    Returns:
        list: Search results
    """
    client = get_opensearch_client("localhost", 9200)

    try:
        query_embedding = get_embeddings(query_text)

        search_query = {
            "size": top_k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": top_k,
                    }
                }
            },
            "_source": ["content", "content_type", "filename"],
        }

        response = client.search(index=INDEX_NAME, body=search_query)
        return response["hits"]["hits"]
    except Exception as e:
        print(f"Semantic search error: {e}")
        return []


def hybrid_search(query_text, top_k=20):
    """
    Perform hybrid search using both keyword and semantic search.

    Args:
        query_text (str): The query text to search for
        top_k (int): Number of results to return

    Returns:
        list: Search results
    """
    client = get_opensearch_client("localhost", 9200)

    try:
        query_embedding = get_embeddings(query_text)

        search_query = {
            "size": top_k,
            "query": {
                "bool": {
                    "should": [
                        {"knn": {"embedding": {"vector": query_embedding, "k": top_k}}},
                        {"match": {"content": query_text}},
                    ]
                }
            },
            "_source": ["content", "content_type", "filename"],
        }

        response = client.search(index=INDEX_NAME, body=search_query)
        return response["hits"]["hits"]
    except Exception as e:
        print(f"Hybrid search error: {e}")
        try:
            fallback_query = {
                "size": top_k,
                "query": {"match": {"content": query_text}},
                "_source": ["content", "content_type", "filename"],
            }
            response = client.search(index=INDEX_NAME, body=fallback_query)
            return response["hits"]["hits"]
        except Exception as e2:
            print(f"Fallback search error: {e2}")
            return []


if __name__ == "__main__":
    from pprint import pprint

    query = "Compare RAG v/s fine-tuning"
    # results = keyword_search(query, top_k=10)
    # results = semantic_search(query, top_k=10)
    results = hybrid_search(query, top_k=10)
    pprint(results)