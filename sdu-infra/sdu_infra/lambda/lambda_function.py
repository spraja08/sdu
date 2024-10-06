import boto3
import base64
import os

def handler(event, context):
    secrets_manager = boto3.client('secretsmanager')
    
    # Generate AES key and IV
    key = os.urandom(16)  # 16 bytes key
    iv = os.urandom(8)    # 8 bytes IV
    
    # Store the key and IV as a secret
    secret_value = base64.b64encode(key + iv).decode('utf-8')

    # Check if 'SecretName' is in the event
    if 'ResourceProperties' not in event or 'SecretName' not in event['ResourceProperties']:
        raise ValueError("SecretName property is missing from the event")
    
    secret_name = event['ResourceProperties']['SecretName']
    
    try:
        # Check if the secret already exists
        secrets_manager.describe_secret(SecretId=secret_name)
        print(f"Secret {secret_name} already exists. Skipping.")
        message = "Key exists. Skipping."

    except secrets_manager.exceptions.ResourceNotFoundException:
        print(f"Secret {secret_name} does not exist. Creating the secret.")
        secrets_manager.create_secret(
            Name=secret_name,
            SecretString=secret_value
        )
        message = "Key Created Successfully."
    
    return {
        'Code': 200,
        'body': message
    }