def get_embeddings(prompt, model="embeddinggemma"):
    import requests
    url = "http://localhost:11434/api/embed"
    data = {
        "model": model,
        "input": prompt,
    }
    response = requests.post(url, json=data)
    response.raise_for_status()

    return response.json().get("embeddings", [None])[0]


def get_opensearch_client(host, port):
    from opensearchpy import OpenSearch
    client = OpenSearch(
        hosts=[{"host": host, "port": port}], 
        http_compress=True,
        timeout = 30,
        max_retries=3,
        retry_on_timeout=True
    )

    if client.ping():
        print("Connected to OpenSearch")
    else:
        raise ConnectionError("Could not connect to OpenSearch")

    return client



if __name__ == "__main__":
    get_opensearch_client("localhost", 9200)
       
