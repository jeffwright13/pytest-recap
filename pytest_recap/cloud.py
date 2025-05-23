import re


def upload_to_cloud(uri, data):
    if uri.startswith("s3://"):
        return _upload_to_s3(uri, data)
    elif uri.startswith("gs://"):
        return _upload_to_gcs(uri, data)
    elif uri.startswith("azure://") or uri.startswith("https://"):
        return _upload_to_azure(uri, data)
    else:
        raise ValueError(f"Unknown cloud URI scheme: {uri}")


def _upload_to_s3(uri, data):
    import boto3

    m = re.match(r"s3://([^/]+)/(.+)", uri)
    if not m:
        raise ValueError(f"Invalid S3 URI: {uri}")
    bucket, key = m.groups()
    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=data)


def _upload_to_gcs(uri, data):
    from google.cloud import storage

    m = re.match(r"gs://([^/]+)/(.+)", uri)
    if not m:
        raise ValueError(f"Invalid GCS URI: {uri}")
    bucket_name, blob_name = m.groups()
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data)


def _upload_to_azure(uri, data):
    from azure.storage.blob import BlobServiceClient

    m = re.match(r"azure://([^/]+)/(.+)", uri)
    if not m:
        raise ValueError(f"Invalid Azure URI: {uri}")
    container, blob_name = m.groups()
    conn_str = None  # Use default env var or config
    bsc = BlobServiceClient.from_connection_string(conn_str) if conn_str else BlobServiceClient()
    container_client = bsc.get_container_client(container)
    container_client.upload_blob(blob_name, data, overwrite=True)
