"""Credential redaction on the repr / diagnostics path (no database required).

`__repr__` of the COPY INTO constructs is documented "for debugging / logging purposes only", so a
repr (or a pytest assertion dump that calls one) must never render cloud credentials. See
Helix 2878a12e.
"""

import pytest

from tidbcloudlake_sqlalchemy.dml import (
    REDACTED,
    AmazonS3,
    AzureBlobStorage,
    CopyIntoTable,
    CopyIntoTableOptions,
    GoogleCloudStorage,
    StageClause,
    CSVFormat,
)

S3_SECRET_ACCESS_KEY = "S3cr3t/Acc3ss+Key+Value"
S3_MASTER_KEY = "master-key-value-must-not-appear"
S3_SECURITY_TOKEN = "session-token-value-must-not-appear"
AZURE_ACCOUNT_KEY = "azure-account-key-value-must-not-appear"
GCS_CREDENTIAL = "eyJ0eXBlIjoic2VydmljZV9hY2NvdW50IiwiZm9vIjoiYmFyIn0="

SECRETS = [
    S3_SECRET_ACCESS_KEY,
    S3_MASTER_KEY,
    S3_SECURITY_TOKEN,
    AZURE_ACCOUNT_KEY,
    GCS_CREDENTIAL,
]


def _assert_no_secrets(rendered: str) -> None:
    for secret in SECRETS:
        assert secret not in rendered, f"credential leaked into repr: {rendered!r}"
    assert REDACTED in rendered


def test_amazon_s3_repr_redacts_every_credential():
    s3 = AmazonS3(
        uri="s3://bucket/path/",
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key=S3_SECRET_ACCESS_KEY,
        endpoint_url="https://s3.amazonaws.com",
        enable_virtual_host_style=True,
        master_key=S3_MASTER_KEY,
        region="us-east-1",
        security_token=S3_SECURITY_TOKEN,
    )
    rendered = repr(s3)
    _assert_no_secrets(rendered)
    assert "AKIAIOSFODNN7EXAMPLE" not in rendered
    # Non-secret routing information stays visible so the repr remains useful for debugging.
    assert "s3://bucket/path/" in rendered
    assert "us-east-1" in rendered


def test_amazon_s3_repr_works_with_only_the_required_fields():
    """Regression: the old repr indexed unset attributes and raised AttributeError."""
    rendered = repr(
        AmazonS3(uri="s3://bucket/", access_key_id="AK", secret_access_key="SK")
    )
    _assert_no_secrets(rendered)
    assert "s3://bucket/" in rendered


def test_azure_blob_repr_redacts_account_key():
    storage = AzureBlobStorage(
        uri="azblob://container/path/",
        account_name="account",
        account_key=AZURE_ACCOUNT_KEY,
    )
    rendered = repr(storage)
    _assert_no_secrets(rendered)
    assert "azblob://container/path/" in rendered
    assert "account" in rendered


def test_google_cloud_storage_repr_redacts_service_account_key():
    storage = GoogleCloudStorage(uri="gcs://bucket/path/", credentials=GCS_CREDENTIAL)
    rendered = repr(storage)
    _assert_no_secrets(rendered)
    assert "gcs://bucket/path/" in rendered


def test_copy_into_table_repr_does_not_leak_through_the_nested_storage_clause():
    stmt = CopyIntoTable(
        target=StageClause(name="target_stage", path="out/"),
        from_=AmazonS3(
            uri="s3://bucket/in/",
            access_key_id="AK",
            secret_access_key=S3_SECRET_ACCESS_KEY,
            security_token=S3_SECURITY_TOKEN,
        ),
        file_format=CSVFormat(),
        options=CopyIntoTableOptions(on_error="CONTINUE"),
    )
    _assert_no_secrets(repr(stmt))


@pytest.mark.parametrize("secret", [None, ""])
def test_unset_credentials_are_reported_as_unset(secret):
    s3 = AmazonS3(uri="s3://bucket/", access_key_id="AK", secret_access_key="")
    s3.master_key = secret
    assert "<unset>" in repr(s3)


@pytest.mark.parametrize(
    "storage",
    [
        lambda uri: AmazonS3(
            uri=uri,
            access_key_id="key",
            secret_access_key="secret",
            endpoint_url="https://user:secret-endpoint@storage.example/?token=endpoint-token",
        ),
        lambda uri: AzureBlobStorage(
            uri=uri.replace("s3:", "azblob:"),
            account_name="account",
            account_key="secret",
        ),
        lambda uri: GoogleCloudStorage(
            uri=uri.replace("s3:", "gcs:"), credentials="secret"
        ),
    ],
)
def test_storage_uri_diagnostics_redact_without_mutating_execution_values(storage):
    uri = "s3://user:uri-password@bucket/path?token=signed-query#fragment-token"
    clause = storage(uri)
    rendered = repr(clause)
    for value in [
        "uri-password",
        "signed-query",
        "fragment-token",
        "secret-endpoint",
        "endpoint-token",
    ]:
        assert value not in rendered
    assert "bucket/path" in rendered
    assert "signed-query" in clause.uri
    if isinstance(clause, AmazonS3):
        assert "endpoint-token" in clause.endpoint_url


@pytest.mark.parametrize(
    "uri",
    [
        "http://user:uri-password@bucket/path?token=signed-query",
        "s3://[invalid?token=signed-query",
    ],
)
def test_invalid_storage_uri_errors_do_not_echo_credentials(uri):
    with pytest.raises(ValueError) as error:
        AmazonS3(uri=uri, access_key_id="key", secret_access_key="secret")
    assert "uri-password" not in str(error.value)
    assert "signed-query" not in str(error.value)
