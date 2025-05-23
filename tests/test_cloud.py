import pytest
from pytest_recap.cloud import _upload_to_azure, _upload_to_gcs, _upload_to_s3

try:
    import moto
except ImportError:
    moto = None

pytestmark = pytest.mark.usefixtures("mocker")


def test_upload_to_s3_success(mocker):
    # Minimal in-memory S3 fake
    class FakeS3Client:
        def __init__(self):
            self.buckets = {}

        def create_bucket(self, Bucket):
            self.buckets[Bucket] = {}

        def put_object(self, Bucket, Key, Body):
            self.buckets.setdefault(Bucket, {})[Key] = Body

        def get_object(self, Bucket, Key):
            # Simulate boto3's streaming body with bytes
            class Body:
                def __init__(self, data):
                    self._data = data

                def read(self):
                    return self._data

            return {"Body": Body(self.buckets[Bucket][Key])}

    fake_s3 = FakeS3Client()
    mocker.patch("boto3.client", return_value=fake_s3)

    bucket = "mybucket"
    key = "recap/test.json"
    data = b'{"foo": "bar"}'
    s3_uri = f"s3://{bucket}/{key}"

    fake_s3.create_bucket(Bucket=bucket)
    _upload_to_s3(s3_uri, data)
    obj = fake_s3.get_object(Bucket=bucket, Key=key)
    assert obj["Body"].read() == data


def test_upload_to_gcs_success(mocker):
    mock_blob = mocker.Mock()
    mock_bucket = mocker.Mock()
    mock_client = mocker.patch("google.cloud.storage.Client")
    mock_client.return_value.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    gcs_uri = "gs://mybucket/recap/test.json"
    data = b'{"foo": "bar"}'
    _upload_to_gcs(gcs_uri, data)
    mock_client.return_value.bucket.assert_called_with("mybucket")
    mock_bucket.blob.assert_called_with("recap/test.json")
    mock_blob.upload_from_string.assert_called_with(data)


def test_upload_to_azure_success(mocker):
    mocker.Mock()
    mock_container_client = mocker.Mock()
    mock_blob_service_client = mocker.patch("azure.storage.blob.BlobServiceClient")
    mock_blob_service_client.from_connection_string.return_value = mock_blob_service_client
    mock_blob_service_client.return_value = mock_blob_service_client
    mock_blob_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.upload_blob.return_value = None
    azure_uri = "azure://mycontainer/recap/test.json"
    data = b'{"foo": "bar"}'
    _upload_to_azure(azure_uri, data)
    mock_blob_service_client.get_container_client.assert_called_with("mycontainer")
    mock_container_client.upload_blob.assert_called()


def test_upload_invalid_scheme():
    with pytest.raises(ValueError):
        from pytest_recap.cloud import upload_to_cloud

        upload_to_cloud("ftp://foo/bar.json", b"data")
