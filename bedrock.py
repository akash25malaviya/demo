# program to invoke bedrock model, @thiru

import boto3
import json
from botocore.exceptions import ClientError
from config import BedrockConfig

def create_bedrock_client():
  
    return boto3.client(
        service_name="bedrock-runtime",
        region_name=BedrockConfig.AWS_REGION,
        aws_access_key_id=BedrockConfig.aws_access_key_id,
        aws_secret_access_key=BedrockConfig.aws_secret_access_key
    )

def invoke_bedrock_model(client, model_id, input_text):
    
    try:
        
        payload = {
            "inputText": input_text,
            "textGenerationConfig": {
                "maxTokenCount": 3072,
                "stopSequences": [],
                "temperature": 0.7,
                "topP": 0.9
            },
        }
        
        
        request_body = json.dumps(payload)
        
        
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=request_body
        )
        
        
        response_payload = json.loads(response["body"].read().decode("utf-8"))
        return response_payload.get("results", [{}])[0].get("outputText", "No output received.")
    except (ClientError, Exception) as e:
        return f"Error invoking Bedrock model: {str(e)}"

if __name__ == "__main__":
   
    bedrock_client = create_bedrock_client()

    
    input_text = "Explain the purpose of root cause analysis in business operations."

    
    model_response = invoke_bedrock_model(bedrock_client, BedrockConfig.MODEL_ID, input_text)

    
    print("Response from Amazon Titan Text G1 - Premier:")
    print(model_response)
