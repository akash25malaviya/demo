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
from typing import List, Optional
from bson import ObjectId
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import asyncio
from config import Config
from log_text import logger
from titan_rca_provider import TitanRCAProvider

# pls change db name 
client = MongoClient(Config.MONGO_CONNECTION_STRING)
db = client["Test-AI"]
incidents_collection = db["incidentsCopy"]
rca_collection = db["rca"]


class IncidentTimeAction(BaseModel):
    action: Optional[str] = None
    timestamp: Optional[str] = None


class ActionPlan(BaseModel):
    action: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None


class Attachment(BaseModel):
    file_name: Optional[str] = None
    file_url: Optional[str] = None


class RCA(BaseModel):
    rcaId: Optional[str] = None
    incidentId: Optional[str] = None
    incidentTitle: Optional[str] = None
    dateOfIncident: Optional[str] = None
    reportedBy: Optional[str] = None
    impactLevel: Optional[str] = None
    durationOfImpact: Optional[str] = None
    affectedApplications: Optional[str] = None
    incidentOwner: Optional[str] = None
    incidentTimeline: Optional[List[IncidentTimeAction]] = []
    rcaDescription: Optional[str] = None
    probableCauses: Optional[str] = None
    impactOnBusiness: Optional[str] = None
    financialImpact: Optional[str] = None
    numberOfUsersAffected: Optional[str] = None
    immediateCause: Optional[str] = None
    rootCause: Optional[str] = None
    actionTakenToResolve: Optional[str] = None
    suggestions: Optional[str] = None
    resolutions: Optional[str] = None
    resolutionDateTime: Optional[str] = None
    shortTermFixes: Optional[str] = None
    longTermPreventiveActions: Optional[str] = None
    keyTakeaways: Optional[str] = None
    processImprovements: Optional[str] = None
    actionPlanItems: Optional[List[ActionPlan]] = []
    recommendedActions: Optional[str] = None
    additionalNotes: Optional[str] = None
    attachments: Optional[List[Attachment]] = []
    createdAt: Optional[datetime] = None
    applicationId: Optional[str] = None
    approvalBy: Optional[str] = None
    approvalDate: Optional[str] = None
    status: Optional[str] = None


class IncidentRequest(BaseModel):
    incident_id: str


class RCAResponse(BaseModel):
    incident_id: str
    rca: dict



def get_rca_provider():
    return TitanRCAProvider()


#  serialize BSON
def serialize_bson(doc: dict) -> dict:
    """
    Converts BSON types (e.g., ObjectId) to JSON-serializable types.
    """
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
    return doc


# here createe RCA Document
def create_rca_document(incident_id: str, rca_data: dict, tags: list, version: str):
    """
    Create an RCA document based on the updated schema.
    """
    timestamp = datetime.now(timezone.utc)
    rca_document = RCA(
        rcaId=str(ObjectId()),  
        incidentId=incident_id,
        rcaDescription=rca_data.get("rcaDescription"),
        probableCauses=rca_data.get("probable_causes"),
        impactOnBusiness=rca_data.get("impacts"),
        rootCause=rca_data.get("root_cause"),
        recommendedActions=rca_data.get("recommended_actions"),
        createdAt=timestamp,
        status="Open",  
        tags=tags,
    )
    return rca_document.model_dump()  


# Background Task to Watch `incidentsCopy`
async def watch_incidents_copy(rca_provider: TitanRCAProvider):
    logger.info("Starting MongoDB Change Stream to watch 'incidentsCopy' collection for new entries.")
    with incidents_collection.watch([{"$match": {"operationType": "insert"}}]) as stream:
        for change in stream:
            new_incident = change["fullDocument"]
            incident_id = new_incident["_id"]
            description = new_incident.get("description", "")
            tags = new_incident.get("tags", [])

            logger.info(f"New entry detected in 'incidentsCopy' collection with incident_id: {incident_id}")
            logger.debug(f"New incident details - Description: '{description}', Tags: {tags}")

            # Check if RCA already exists
            if not rca_collection.find_one({"incidentId": incident_id}):
                try:
                    rca_data = await rca_provider.generate_rca(description, tags)
                    rca_document = create_rca_document(incident_id, rca_data, tags, version="1.0")
                    rca_collection.insert_one(rca_document)
                    logger.info(f"Generated and stored RCA for new incident with ID: {incident_id}")
                except Exception as e:
                    logger.error(f"Failed to generate RCA for new incident with ID: {incident_id} - {e}")


# Lifespan Event Handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    rca_provider = get_rca_provider()
    watcher_task = asyncio.create_task(watch_incidents_copy(rca_provider))
    logger.info("Application startup: Background task for monitoring new incidents initiated.")

    yield

    watcher_task.cancel()
    try:
        await watcher_task
    except asyncio.CancelledError:
        logger.info("Application shutdown: Background task for monitoring new incidents terminated.")


# FastAPI App
app = FastAPI(lifespan=lifespan)


# Generate RCA for a Given Incident, endpoint to generate RCA
@app.post("/generate-rca", response_model=RCAResponse)
async def generate_rca_for_incident(
    incident_request: IncidentRequest,
    rca_provider: TitanRCAProvider = Depends(get_rca_provider),
):
    incident_id = incident_request.incident_id
    logger.info(f"API request received for incident_id: {incident_id}")

    # Check if RCA already exists
    existing_rca = rca_collection.find_one({"incidentId": incident_id})
    if existing_rca:
        logger.info(f"Returning existing RCA for incident_id: {incident_id}")
        return RCAResponse(
            incident_id=incident_id,
            rca=serialize_bson(existing_rca),  
        )

    # Retrieve incident from `incidentsCopy`
    incident = incidents_collection.find_one({"_id": incident_id})
    if not incident:
        logger.error(f"Incident not found in incidentsCopy collection for incident_id: {incident_id}")
        raise HTTPException(status_code=404, detail="Incident not found in incidentsCopy collection")

    # Generate RCA
    try:
        rca_data = await rca_provider.generate_rca(
            description=incident.get("description", ""),
            tags=incident.get("tags", []),
        )
    except Exception as e:
        logger.error(f"Error generating RCA for incident_id: {incident_id} - {e}")
        raise HTTPException(status_code=500, detail="Error generating RCA")

    # Create RCA Document and Store
    rca_document = create_rca_document(incident_id, rca_data, incident.get("tags", []), version="1.0")
    rca_collection.replace_one({"incidentId": incident_id}, rca_document, upsert=True)

    logger.info(f"New RCA stored for incident_id: {incident_id}")
    return RCAResponse(
        incident_id=incident_id,
        rca=serialize_bson(rca_document),  # Serialize BSON document
    )
