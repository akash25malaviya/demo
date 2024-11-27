# Author: Thirumurugan
# Email: thirumurugan.chokkalingam@g10x.com
# Phone: +91 8883187597
# GitHub: https://github.com/ThiruLoki
#
# Project: GlassX 
# Description: code for GlassX - Bedrock model integration

import boto3
import json
from config import BedrockConfig
from botocore.exceptions import ClientError
import logging


logger = logging.getLogger("TitanRCAProvider")
logger.setLevel(logging.INFO)


class TitanRCAProvider:
    def __init__(self):
        
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=BedrockConfig.AWS_REGION,
            aws_access_key_id=BedrockConfig.aws_access_key_id,
            aws_secret_access_key=BedrockConfig.aws_secret_access_key
        )

    async def generate_rca(self, description: str, tags: list) -> dict:
       
        #  payload for the Bedrock API
        request_payload = {
            "inputText": f"Generate a concise Root Cause Analysis (RCA) report for the following incident.\n\n"
                         f"Description: {description}\n"
                         f"Tags: {', '.join(tags)}\n\n"
                         f"Provide the analysis with the following structure:\n"
                         f"1. RCA Description: A brief overview of the issue.\n"
                         f"2. Probable Causes (short and precise):\n   - Describe the reasons.\n"
                         f"3. Impacts (concise and actionable):\n   - Explain the effects.\n"
                         f"4. Recommended Actions (clear steps):\n   - Provide solutions.\n",
            "textGenerationConfig": {
                "maxTokenCount": 300,
                "temperature": 0.5,
                "topP": 0.9
            }
        }

        try:
            # Invoke the Bedrock model
            response = self.client.invoke_model(
                modelId=BedrockConfig.MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_payload)
            )

            
            if 'body' not in response:
                logger.error("No body in the response from Bedrock model.")
                return {"error": "No response body from Bedrock model."}

            response_body = json.loads(response['body'].read().decode('utf-8'))
            generated_text = response_body['results'][0]['outputText']

            
            formatted_output = self.format_rca_output(generated_text)

            
            formatted_output["rcaDescription"] = self.extract_section(
                generated_text, "RCA Description", "Probable Causes"
            )

            return formatted_output

        except ClientError as e:
            logger.error(f"ClientError: {e.response['Error']['Message']}")
            return {"error": "RCA generation failed due to a client error."}

        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return {"error": "RCA could not be generated."}

    def format_rca_output(self, generated_text: str) -> dict:
        
        try:
            probable_causes = self.clean_text(
                self.extract_section(generated_text, "Probable Causes", "Impacts")
            )
            impacts = self.clean_text(
                self.extract_section(generated_text, "Impacts", "Recommended Actions")
            )
            recommended_actions = self.clean_text(
                self.extract_section(generated_text, "Recommended Actions", None)
            )

            return {
                "probable_causes": probable_causes,
                "impacts": impacts,
                "recommended_actions": recommended_actions
            }
        except Exception as e:
            logger.error(f"Error formatting RCA output: {e}")
            return {"error": "Error in formatting RCA response."}

    def extract_section(self, text: str, start_keyword: str, end_keyword: str = None) -> str:
        """
        Extracts a section of text between two keywords.
        """
        try:
            start_idx = text.find(start_keyword)
            if start_idx == -1:
                logger.warning(f"{start_keyword} section not found in text.")
                return f"{start_keyword} section not found."

            end_idx = text.find(end_keyword, start_idx) if end_keyword else len(text)
            if end_idx == -1:
                end_idx = len(text)  

            return text[start_idx + len(start_keyword):end_idx].strip()
        except Exception as e:
            logger.error(f"Error extracting section {start_keyword}: {e}")
            return ""

    def clean_text(self, text: str) -> str:
        """
        Cleans and formats text for readability:
        - Removes unnecessary numbering or colons.
        - Ensures consistent bullet-point formatting.
        """
        try:
           
            text = text.replace("2.", "").replace("3.", "").replace(":", "").strip()

           
            lines = text.split("\n")
            formatted_lines = [line.strip("- ").strip() for line in lines if line.strip()]
            return "\n- " + "\n- ".join(formatted_lines) if formatted_lines else text
        except Exception as e:
            logger.error(f"Error cleaning text: {e}")
            return text.strip()
