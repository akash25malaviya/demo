# Author: Thirumurugan
# Email: thirumurugan.chokkalingam@g10x.com
# Phone: +91 8883187597
# GitHub: https://github.com/ThiruLoki
#
# Project: GlassX 
# Description: code for GlassX - Bedrock model integration

# file name: titan_rca_provider
import boto3
import json
from config import Config
from botocore.exceptions import ClientError

class TitanRCAProvider:
    def __init__(self):
        
        self.client = boto3.client('bedrock', region_name='us-east-1')  

    async def generate_rca(self, description: str, tags: list):
        
        request_payload = {
            "inputText": f"Generate RCA for incident. Description: {description}. Tags: {', '.join(tags)}",
            "textGenerationConfig": {
                "maxTokenCount": 512,
                "temperature": 0.5,
                "topP": 0.9
            }
        }

        try:
            
            response = self.client.invoke_model(
                modelId="amazon.titan-text-express-v1",
                body=json.dumps(request_payload)
            )

            
            response_body = json.loads(response['body'].read())
            generated_text = response_body['results'][0]['outputText']
            return generated_text

        except ClientError as e:
            print(f"An error occurred: {e}")
            return "RCA could not be generated."
