# gpt3_rca_provider.py

from config import Config
import openai
from rca_provider import RCAProvider
import re

class GPT3TurboRCAProvider(RCAProvider):
    def __init__(self):
        openai.api_key = Config.OPENAI_API_KEY

    async def generate_rca(self, description: str, tags: list) -> dict:
        # prompt for asking the model
        prompt = (
            f"Generate a Root Cause Analysis (RCA) report based on the following incident details:\n\n"
            f"Description: {description}\n"
            f"Tags: {', '.join(tags)}\n\n"
            f"Provide a step-by-step breakdown for each of the following sections:\n\n"
            f"1. Probable Causes:\n"
            f"   - List possible causes in a detailed, step-by-step manner explaining why each one might lead to this issue.\n\n"
            f"2. Impacts:\n"
            f"   - Describe the potential impacts of this issue on users and the system, providing specific examples if applicable.\n\n"
            f"3. Recommended Actions:\n"
            f"   - Provide a detailed, actionable list of steps that should be taken to resolve the issue. Be specific in describing each action, including who might be responsible and what tools might be used.\n"
        )

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an RCA generation assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,  # tune token for more or less response
            temperature=0.5  # Lower temperature for more focused and deterministic output
        )

        rca_content = response['choices'][0]['message']['content']
        
        # Print raw response for debugging- i got u
        print("GPT-3.5 Turbo Response:", rca_content)
        
        # Use regular expressions to find each section more flexibly
        probable_causes = re.search(r"(?<=Probable Causes:)[\s\S]*?(?=Impacts:|$)", rca_content)
        impacts = re.search(r"(?<=Impacts:)[\s\S]*?(?=Recommended Actions:|$)", rca_content)
        recommended_actions = re.search(r"(?<=Recommended Actions:)[\s\S]*$", rca_content)

        return {
            "probable_causes": probable_causes.group(0).strip() if probable_causes else "Could not generate probable causes.",
            "impacts": impacts.group(0).strip() if impacts else "Could not generate impacts.",
            "recommended_actions": recommended_actions.group(0).strip() if recommended_actions else "Could not generate recommended actions."
        }
