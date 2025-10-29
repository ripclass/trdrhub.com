#!/bin/bash
set -e

echo "Waiting for MinIO to be ready..."
sleep 10

# Configure mc alias
mc alias set myminio $MINIO_ENDPOINT $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# Create region-specific buckets
REGIONS=("bd" "eu" "sg")
BUCKETS=("docs" "backups")

for bucket in "${BUCKETS[@]}"; do
    for region in "${REGIONS[@]}"; do
        bucket_name="lcopilot-${bucket}-${region}-dev"
        echo "Creating bucket: $bucket_name"

        # Create bucket if it doesn't exist
        if ! mc ls myminio/$bucket_name > /dev/null 2>&1; then
            mc mb myminio/$bucket_name

            # Set bucket encryption
            mc encrypt set sse-s3 myminio/$bucket_name

            # Enable versioning
            mc version enable myminio/$bucket_name

            # Set lifecycle policy for docs buckets
            if [ "$bucket" = "docs" ]; then
                cat > /tmp/lifecycle.json << EOF
{
    "Rules": [
        {
            "ID": "transition_to_ia",
            "Status": "Enabled",
            "Filter": {},
            "Transitions": [
                {
                    "Days": 30,
                    "StorageClass": "STANDARD_IA"
                },
                {
                    "Days": 90,
                    "StorageClass": "GLACIER"
                }
            ],
            "NoncurrentVersionExpiration": {
                "NoncurrentDays": 90
            }
        }
    ]
}
EOF
                mc ilm import myminio/$bucket_name < /tmp/lifecycle.json
            fi

            echo "✓ Bucket $bucket_name configured successfully"
        else
            echo "✓ Bucket $bucket_name already exists"
        fi
    done
done

# Create test object to verify encryption
echo "Testing encryption..."
echo "test-content-$(date)" > /tmp/test.txt
mc cp /tmp/test.txt myminio/lcopilot-docs-bd-dev/test.txt
mc stat myminio/lcopilot-docs-bd-dev/test.txt

echo "✅ All buckets created and configured successfully!"