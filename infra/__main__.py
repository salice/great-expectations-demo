from pulumi import Output, export
import pulumi_aws as aws
import pulumi_github as github
import os
from dotenv import load_dotenv
load_dotenv()

github_account = "salice"
github_repo = "great-expectations-demo"
bucket = aws.s3.Bucket(os.getenv("BUCKET_NAME"))
bucket_name = bucket.id
user = os.getenv("AWS_USER_ID")
current = aws.get_partition()
user_id = os.getenv("AWS_USER_ID")
principal_str = f"arn:aws:iam::{current}:user/{user_id}"
oidc_provider = aws.iam.OpenIdConnectProvider("github action",
            client_id_lists=[f"https://github.com/{github_account}", 
                             "sts.amazonaws.com"],
            thumbprint_lists=["6938fd4d98bab03faadb97b34396831e3780aea1"],
            url="https://token.actions.githubusercontent.com")

gx_role = aws.iam.Role("gx-github-role",
            assume_role_policy=Output.json_dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
            "Principal": {
                "Federated": [oidc_provider.arn]
            },
            "Action": ["sts:AssumeRoleWithWebIdentity"],
            "Condition": {
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": 
                    "repo:{}/{}:*".format(github_account, github_repo) 
                },
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                }
            }

            }]

         }))

policy_policy_document = aws.iam.get_policy_document(
    statements=[aws.iam.GetPolicyDocumentStatementArgs(
        effect="Allow",
        actions=["s3:GetObject",
                "s3:GetObjectVersion",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetBucketLocation"],
        resources=[Output.format("arn:aws:s3:::{0}/*", bucket_name),
                Output.format("arn:aws:s3:::{0}", bucket_name),],
)])
github_policy = aws.iam.Policy("github-action-policy",
               description="oidc connection github aws",
               policy=policy_policy_document.json)

policy_policy = aws.iam.Policy("gx-github-policy",
    description="A test policy",
    policy=policy_policy_document.json)
gx_attach_policy = aws.iam.PolicyAttachment("github-action-role-attach",
    users=[user],
    roles=[gx_role.name],
    policy_arn=policy_policy.arn)

# gx_actions_secret = github.ActionsSecret("role_arn",
#                      repository=github_repo,
#                      secret_name="ROLE_ARN",
#                      plaintext_value=gx_role.arn)

# def iam_role_github_general_access(bucket_name):
#     return Output.json_dumps({
#         "Version": "2012-10-17",
#         "Statement": [{
#             "Effect": "Allow",
#             "Principal": { "AWS": principal_str},
#             "Action": [
#                 "s3:GetObject",
#                 "s3:GetObjectVersion",
#                 "s3:PutObject",
#                 "s3:DeleteObject",
#                 "s3:ListBucket",
#                 "s3:GetBucketLocation"
#             ],
#             "Resource": [
#                 Output.format("arn:aws:s3:::{0}/*", bucket_name),
#                 Output.format("arn:aws:s3:::{0}", bucket_name),
#             ]
#         }, 
#         {
#             "Effect": "Allow",
#             "Principal": {
#                 "Federated": [oidc_provider.arn]
#             },
#             "Action": ["sts:AssumeRoleWithWebIdentity"],
#             "Condition": {
#                 "StringLike": {
#                     "token.actions.githubusercontent.com:sub": 
#                     Output.format("repo:{0}/{1}:*", github_account, github_repo)
#                 },
#                 "StringEquals": {
#                     "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
#                 }
#             }
#         }]
#     })


# bucket_policy = aws.s3.BucketPolicy("gx-policy",
#     bucket=bucket_name,
#     policy=iam_role_github_general_access(bucket_name))

# Export the name of the bucket
export('bucket_name', bucket.id)
export("role arn", gx_role.arn)