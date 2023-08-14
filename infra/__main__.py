from pulumi import Output, export
from pulumi_aws import s3
import os
from dotenv import load_dotenv
load_dotenv()

bucket = s3.Bucket(os.getenv("BUCKET_NAME"))
account_id = os.getenv("AWS_ACCOUNT_ID")
user_id = os.getenv("AWS_USER_ID")
principal_str = f"arn:aws:iam::{account_id}:user/{user_id}"

def public_read_policy_for_bucket(bucket_name):
    return Output.json_dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": { "AWS": principal_str},
            "Action": [
                "s3:GetObject",
                "s3:GetObjectVersion",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": [
                Output.format("arn:aws:s3:::{0}/*", bucket_name),
                Output.format("arn:aws:s3:::{0}", bucket_name),
            ]
        }]
    })

bucket_name = bucket.id
bucket_policy = s3.BucketPolicy("gx-policy",
    bucket=bucket_name,
    policy=public_read_policy_for_bucket(bucket_name))

# Export the name of the bucket
export('bucket_name', bucket.id)