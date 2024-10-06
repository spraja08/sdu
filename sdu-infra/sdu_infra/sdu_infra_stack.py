from aws_cdk import (
    Stack, aws_s3 as s3, aws_iam as iam, RemovalPolicy,
    aws_lambda as _lambda, custom_resources as cr, Duration,
    CustomResource
)
from constructs import Construct
import boto3
import base64
import os

class SduInfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        bucket = s3.Bucket(self, "sdu-incoming",
            bucket_name=f"sdu-incoming-{self.account}-{self.region}",
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        role = iam.Role(self, "sdu-role", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))
        
        policy = iam.PolicyStatement(
            effect = iam.Effect.ALLOW,
            actions = [
                's3:*',
                "secretsmanager:DescribeSecret", 
                "secretsmanager:GetSecretValue"
            ],
            resources= ['*'],
        )
        role.add_to_policy(policy)
        
        #idempotent creation of the key and iv
        lambda_function = _lambda.Function(self, "GenerateKeyIVFunction",
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler="lambda_function.handler",
            code=_lambda.Code.from_asset(os.path.join(os.path.dirname(__file__), "lambda")),
            timeout=Duration.seconds(30),        
        )
        # Grant the Lambda function permissions to create secrets
        lambda_function.add_to_role_policy(iam.PolicyStatement(
            actions=["secretsmanager:CreateSecret", "secretsmanager:PutSecretValue", 
                     "secretsmanager:DescribeSecret", "secretsmanager:GetSecretValue"],
            resources=["*"]
        ))
        
        # Define the custom resource to invoke the Lambda function
        provider = cr.Provider(self, "Provider",
            on_event_handler=lambda_function
        )
        
        custom_resource = CustomResource(self, "CustomResource",
            service_token=provider.service_token,
            properties={
                "SecretName": "data-key"
            }
        )
