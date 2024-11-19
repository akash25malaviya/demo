# Author: Thirumurugan
# Email: thirumurugan.chokkalingam@g10x.com
# Phone: +91 8883187597
# GitHub: https://github.com/ThiruLoki
#
# Project: GlassX 
# Description: code for GlassX - Bedrock model integration

# file name: main.py

from fastapi import FastAPI, HTTPException, Depends
from pymongo import MongoClient
from pydantic import BaseModel
from gpt3_rca_provider import GPT3TurboRCAProvider
from config import Config
from log_text import logger  
import asyncio
from contextlib import asynccontextmanager
from titan_rca_provider import TitanRCAProvider



client = MongoClient(Config.MONGO_CONNECTION_STRING)
db = client["Test-AI"]  
incidents_collection = db["incidentsCopy"]
rca_collection = db["rca"]

# Dependency injection for RCA provider
def get_rca_provider():
    return GPT3TurboRCAProvider()
# def get_rca_provider():
#     return TitanRCAProvider()

# Background task to monitor changes in `schema - incidentsCopy`
async def watch_incidents_copy(rca_provider: GPT3TurboRCAProvider):
    logger.info("Starting MongoDB Change Stream to watch 'incidentsCopy' collection for new entries.")
    with incidents_collection.watch([{"$match": {"operationType": "insert"}}]) as stream:
        for change in stream:
            new_incident = change["fullDocument"]
            incident_id = new_incident["_id"]
            description = new_incident.get("description", "")
            tags = new_incident.get("tags", [])
            
            logger.info(f"New entry detected in 'incidentsCopy' collection with incident_id: {incident_id}")
            logger.debug(f"New incident details - Description: '{description}', Tags: {tags}")

            # Check if RCA already exists for this incident
            if not rca_collection.find_one({"incidentId": incident_id}):
                try:
                    # Generate RCA and store it in `rca` collection
                    rca_data = await rca_provider.generate_rca(description, tags)
                    rca_collection.insert_one({
                        "incidentId": incident_id,
                        "rca": rca_data
                    })
                    logger.info(f"Generated and stored RCA for new incident with ID: {incident_id}")
                except Exception as e:
                    logger.error(f"Failed to generate RCA for new incident with ID: {incident_id} - {e}")

# Lifespan event handler using async context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    rca_provider = get_rca_provider()
    watcher_task = asyncio.create_task(watch_incidents_copy(rca_provider))
    logger.info("Application startup: Background task for monitoring new incidents initiated.")
    
    yield  # Control will return here when the application shuts down
    
    # Cancel the background watcher task on shutdown
    watcher_task.cancel()
    try:
        await watcher_task
    except asyncio.CancelledError:
        logger.info("Application shutdown: Background task for monitoring new incidents terminated.")

# Initialize FastAPI app with lifespan
# i've used this since on-time is depreciated, refer online for more.
app = FastAPI(lifespan=lifespan)

# Define Pydantic models
class IncidentRequest(BaseModel):
    incident_id: str

class RCAResponse(BaseModel):
    incident_id: str
    rca: dict

# API endpoint starts here...
@app.post("/generate-rca", response_model=RCAResponse)
async def generate_rca_for_incident(
    incident_request: IncidentRequest,
    rca_provider: GPT3TurboRCAProvider = Depends(get_rca_provider)
):
    incident_id = incident_request.incident_id
    logger.info(f"API request received for incident_id: {incident_id}")

    # Step 1: Check if RCA already exists in the `rca` collection
    existing_rca = rca_collection.find_one({"incidentId": incident_id})
    if existing_rca:
        logger.info(f"RCA already exists for incident_id: {incident_id}, retrieving existing RCA.")
        return RCAResponse(incident_id=incident_id, rca=existing_rca["rca"])

    # Step 2: Retrieve the incident from `schema - incidentsCopy`, if required change in future
    incident = incidents_collection.find_one({"_id": incident_id})
    if incident is None:
        logger.error(f"Incident not found in incidentsCopy collection for incident_id: {incident_id}")
        raise HTTPException(status_code=404, detail="Incident not found in incidentsCopy collection")

    # Step 3: Generate RCA using the description and tags from the incident
    description = incident.get("description", "")
    tags = incident.get("tags", [])
    logger.info(f"Generating RCA for incident_id: {incident_id} with description: '{description}' and tags: {tags}")

    try:
        rca_data = await rca_provider.generate_rca(description, tags)
        logger.info(f"RCA generated successfully for incident_id: {incident_id}")
    except Exception as e:
        logger.error(f"Error generating RCA for incident_id: {incident_id} - {e}")
        raise HTTPException(status_code=500, detail="Error generating RCA")

    # Step 4: Store the new RCA in the `rca` collection with `incidentId`
    new_rca_document = {
        "incidentId": incident_id,
        "rca": rca_data
    }
    rca_collection.insert_one(new_rca_document)
    logger.info(f"RCA stored in 'rca' collection for incident_id: {incident_id}")

    return RCAResponse(incident_id=incident_id, rca=rca_data)
