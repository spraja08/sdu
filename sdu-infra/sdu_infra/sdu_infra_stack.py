from aws_cdk import (
    Stack, aws_s3 as s3, aws_iam as iam
)
from constructs import Construct

class SduInfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        bucket = s3.Bucket(self, "XXXXXXXXXXXX",
            bucket_name=f"sdu-incoming-{self.account}-{self.region}",
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )
        
        role = iam.Role(self, "sdu-role", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))
        
        policy = iam.PolicyStatement(
            effect = iam.Effect.ALLOW,
            actions = [
                's3:*',
                'kms:Encrypt',
                'kms:Decrypt',
                'kms:ReEncrypt*',
                'kms:GenerateDataKey*',
                'kms:DescribeKey',
            ],
            resources= ['*'],
        )
        role.add_to_policy(policy)
        