import boto3
from botocore.exceptions import ClientError


bedrock_client = boto3.client('bedrock', region_name='ap-south-1')

def check_bedrock_models():
    try:
        print("Attempting to list Bedrock models...")
        response = bedrock_client.list_foundation_models()
        print("Response received from Bedrock:")
        
       
        if 'modelSummaries' in response:
            print("Available Bedrock Models:")
            for model in response['modelSummaries']:
                print(f"Model Name: {model['modelName']}, Model ID: {model['modelId']}")
        else:
            print("No models found in the response.")
    except ClientError as e:
        print(f"An error occurred: {e}")

check_bedrock_models()
