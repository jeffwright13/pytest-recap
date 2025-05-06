import pytest
from pytest_recap.cloud import upload_to_azure, upload_to_gcs, upload_to_s3

try:
    import moto
except ImportError:
    moto = None

pytestmark = pytest.mark.usefixtures("mocker")


@pytest.mark.skipif(moto is None, reason="moto not installed")
def test_upload_to_s3_success(tmp_path):
    import boto3
    from moto import mock_s3

    bucket = "mybucket"
    key = "recap/test.json"
    data = b'{"foo": "bar"}'
    s3_uri = f"s3://{bucket}/{key}"
    with mock_s3():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=bucket)
        upload_to_s3(s3_uri, data)
        obj = s3.get_object(Bucket=bucket, Key=key)
        assert obj["Body"].read() == data


def test_upload_to_gcs_success(mocker):
    mock_blob = mocker.Mock()
    mock_bucket = mocker.Mock()
    mock_client = mocker.patch("google.cloud.storage.Client")
    mock_client.return_value.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    gcs_uri = "gs://mybucket/recap/test.json"
    data = b'{"foo": "bar"}'
    upload_to_gcs(gcs_uri, data)
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
    upload_to_azure(azure_uri, data)
    mock_blob_service_client.get_container_client.assert_called_with("mycontainer")
    mock_container_client.upload_blob.assert_called()


def test_upload_invalid_scheme():
    with pytest.raises(ValueError):
        from pytest_recap.cloud import upload_to_cloud

        upload_to_cloud("ftp://foo/bar.json", b"data")
