"""
Shared S3 client factory.

Every S3 client in the app is built here so the storage vendor is one
env var away:

- ``S3_ENDPOINT_URL`` unset -> plain AWS S3 (legacy behavior).
- ``S3_ENDPOINT_URL`` set   -> any S3-compatible store. Currently Supabase
  Storage (``https://<ref>.supabase.co/storage/v1/s3``), which requires
  path-style addressing and SigV4. ``AWS_ACCESS_KEY_ID`` /
  ``AWS_SECRET_ACCESS_KEY`` hold the store's S3 access keys regardless of
  vendor — boto3 reads those names natively.
"""

import os
from typing import Optional

import boto3
from botocore.config import Config


def get_s3_client(region_name: Optional[str] = None, config: Optional[Config] = None):
    """Build an S3 client honoring the S3_ENDPOINT_URL override.

    Args:
        region_name: optional region override; defaults to boto3's normal
            resolution (AWS_REGION / AWS_DEFAULT_REGION env).
        config: optional botocore Config; merged with the S3-compatible
            settings (which take precedence) when an endpoint is set.
    """
    kwargs = {}

    endpoint_url = os.getenv("S3_ENDPOINT_URL") or None
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
        compat = Config(signature_version="s3v4", s3={"addressing_style": "path"})
        config = config.merge(compat) if config is not None else compat

    if config is not None:
        kwargs["config"] = config
    if region_name:
        kwargs["region_name"] = region_name

    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key

    return boto3.client("s3", **kwargs)
