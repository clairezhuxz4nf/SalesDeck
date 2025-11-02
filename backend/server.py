from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Depends, Response, Cookie, Header
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from emergentintegrations.llm.chat import LlmChat, UserMessage
import json
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    picture: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Client(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    industry: str
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ClientCreate(BaseModel):
    name: str
    industry: str
    description: str

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None

class Asset(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: str  # "product_description", "use_case", "general"
    name: str
    content: str
    file_url: Optional[str] = None
    file_data: Optional[str] = None  # Base64 encoded file
    file_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AssetCreate(BaseModel):
    type: str
    name: str
    content: str
    file_url: Optional[str] = None

class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    client_id: str
    client_name: str
    project_scope: str
    notes: str
    status: str = "active"  # active, won, lost
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LeadCreate(BaseModel):
    client_id: str
    project_scope: str
    notes: str

class LeadUpdate(BaseModel):
    client_id: Optional[str] = None
    project_scope: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class SalesDeck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    lead_id: str
    lead_name: str
    content: dict
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DeckGenerateRequest(BaseModel):
    lead_id: str

# Authentication helper
async def get_current_user(session_token: Optional[str] = Cookie(None), authorization: Optional[str] = Header(None)) -> User:
    token = session_token
    if not token and authorization:
        if authorization.startswith('Bearer '):
            token = authorization.replace('Bearer ', '')
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = await db.user_sessions.find_one({"session_token": token})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    if datetime.fromisoformat(session['expires_at']) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    user = await db.users.find_one({"id": session['user_id']}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if isinstance(user['created_at'], str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return User(**user)

# Auth Routes
@api_router.post("/auth/session")
async def create_session(response: Response, session_id: str = Form(...)):
    import httpx
    
    logger.info(f"Creating session for session_id: {session_id[:20]}...")
    
    async with httpx.AsyncClient() as client:
        auth_response = await client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
        
        if auth_response.status_code != 200:
            logger.error(f"Auth service returned {auth_response.status_code}")
            raise HTTPException(status_code=400, detail="Invalid session ID")
        
        user_data = auth_response.json()
        logger.info(f"User data retrieved: {user_data.get('email')}")
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data['email']}, {"_id": 0})
    
    if not existing_user:
        logger.info(f"Creating new user: {user_data['email']}")
        user = User(
            id=user_data['id'],
            email=user_data['email'],
            name=user_data['name'],
            picture=user_data['picture']
        )
        user_dict = user.model_dump()
        user_dict['created_at'] = user_dict['created_at'].isoformat()
        await db.users.insert_one(user_dict)
    else:
        logger.info(f"Existing user found: {user_data['email']}")
    
    # Create session
    session_token = user_data['session_token']
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    session = UserSession(
        user_id=user_data['id'],
        session_token=session_token,
        expires_at=expires_at
    )
    
    session_dict = session.model_dump()
    session_dict['expires_at'] = session_dict['expires_at'].isoformat()
    session_dict['created_at'] = session_dict['created_at'].isoformat()
    
    await db.user_sessions.insert_one(session_dict)
    logger.info(f"Session created successfully for user: {user_data['email']}")
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7*24*60*60,
        path="/"
    )
    
    logger.info("Cookie set successfully")
    return {"success": True, "session_token": session_token}

@api_router.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.post("/auth/logout")
async def logout(response: Response, session_token: Optional[str] = Cookie(None)):
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
        response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"success": True}

# Client Routes
@api_router.post("/clients", response_model=Client)
async def create_client(client_data: ClientCreate, current_user: User = Depends(get_current_user)):
    client = Client(
        user_id=current_user.id,
        **client_data.model_dump()
    )
    
    client_dict = client.model_dump()
    client_dict['created_at'] = client_dict['created_at'].isoformat()
    
    await db.clients.insert_one(client_dict)
    return client

@api_router.get("/clients", response_model=List[Client])
async def get_clients(current_user: User = Depends(get_current_user)):
    clients = await db.clients.find({"user_id": current_user.id}, {"_id": 0}).to_list(1000)
    
    for client in clients:
        if isinstance(client['created_at'], str):
            client['created_at'] = datetime.fromisoformat(client['created_at'])
    
    return clients

@api_router.patch("/clients/{client_id}", response_model=Client)
async def update_client(client_id: str, client_data: ClientUpdate, current_user: User = Depends(get_current_user)):
    update_data = {k: v for k, v in client_data.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    result = await db.clients.update_one(
        {"id": client_id, "user_id": current_user.id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if isinstance(client['created_at'], str):
        client['created_at'] = datetime.fromisoformat(client['created_at'])
    
    return Client(**client)

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, current_user: User = Depends(get_current_user)):
    result = await db.clients.delete_one({"id": client_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"success": True}

# Asset Routes
@api_router.post("/assets/upload")
async def upload_asset(
    file: UploadFile = File(...),
    type: str = Form(...),
    name: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    # Read file content
    file_content = await file.read()
    
    # For text extraction, try to decode
    try:
        content = file_content.decode('utf-8')
    except:
        # If can't decode as text, store as base64
        content = f"[Binary file: {file.filename}]"
    
    asset = Asset(
        user_id=current_user.id,
        type=type,
        name=name,
        content=content,
        file_name=file.filename,
        file_data=base64.b64encode(file_content).decode('utf-8')
    )
    
    asset_dict = asset.model_dump()
    asset_dict['created_at'] = asset_dict['created_at'].isoformat()
    
    await db.assets.insert_one(asset_dict)
    return asset

@api_router.post("/assets", response_model=Asset)
async def create_asset(asset_data: AssetCreate, current_user: User = Depends(get_current_user)):
    asset = Asset(
        user_id=current_user.id,
        **asset_data.model_dump()
    )
    
    asset_dict = asset.model_dump()
    asset_dict['created_at'] = asset_dict['created_at'].isoformat()
    
    await db.assets.insert_one(asset_dict)
    return asset

@api_router.get("/assets", response_model=List[Asset])
async def get_assets(asset_type: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {"user_id": current_user.id}
    if asset_type:
        query["type"] = asset_type
    
    assets = await db.assets.find(query, {"_id": 0}).to_list(1000)
    
    for asset in assets:
        if isinstance(asset['created_at'], str):
            asset['created_at'] = datetime.fromisoformat(asset['created_at'])
    
    return assets

@api_router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: str, current_user: User = Depends(get_current_user)):
    result = await db.assets.delete_one({"id": asset_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"success": True}

# Lead Routes
@api_router.post("/leads", response_model=Lead)
async def create_lead(lead_data: LeadCreate, current_user: User = Depends(get_current_user)):
    # Get client name
    client = await db.clients.find_one({"id": lead_data.client_id, "user_id": current_user.id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    lead = Lead(
        user_id=current_user.id,
        client_name=client['name'],
        **lead_data.model_dump()
    )
    
    lead_dict = lead.model_dump()
    lead_dict['created_at'] = lead_dict['created_at'].isoformat()
    
    await db.leads.insert_one(lead_dict)
    return lead

@api_router.get("/leads", response_model=List[Lead])
async def get_leads(current_user: User = Depends(get_current_user)):
    leads = await db.leads.find({"user_id": current_user.id}, {"_id": 0}).to_list(1000)
    
    for lead in leads:
        if isinstance(lead['created_at'], str):
            lead['created_at'] = datetime.fromisoformat(lead['created_at'])
    
    return leads

@api_router.patch("/leads/{lead_id}", response_model=Lead)
async def update_lead(lead_id: str, lead_data: LeadUpdate, current_user: User = Depends(get_current_user)):
    update_data = {k: v for k, v in lead_data.model_dump().items() if v is not None}
    
    # If client_id is being updated, get new client name
    if 'client_id' in update_data:
        client = await db.clients.find_one({"id": update_data['client_id'], "user_id": current_user.id}, {"_id": 0})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        update_data['client_name'] = client['name']
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    result = await db.leads.update_one(
        {"id": lead_id, "user_id": current_user.id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if isinstance(lead['created_at'], str):
        lead['created_at'] = datetime.fromisoformat(lead['created_at'])
    
    return Lead(**lead)

@api_router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    result = await db.leads.delete_one({"id": lead_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True}

# Sales Deck Routes
@api_router.post("/decks/generate", response_model=SalesDeck)
async def generate_deck(request: DeckGenerateRequest, current_user: User = Depends(get_current_user)):
    # Get lead details
    lead = await db.leads.find_one({"id": request.lead_id, "user_id": current_user.id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get client details
    client = await db.clients.find_one({"id": lead['client_id'], "user_id": current_user.id}, {"_id": 0})
    
    # Get assets
    assets = await db.assets.find({"user_id": current_user.id}, {"_id": 0}).to_list(1000)
    
    # Prepare context for AI
    product_descriptions = [a['content'] for a in assets if a['type'] == 'product_description']
    use_cases = [a['content'] for a in assets if a['type'] == 'use_case']
    
    context = f"""
    Client Information:
    - Name: {client['name']}
    - Industry: {client['industry']}
    - Description: {client['description']}
    
    Lead Information:
    - Project Scope: {lead['project_scope']}
    - Notes: {lead['notes']}
    
    Product Information:
    {chr(10).join(product_descriptions) if product_descriptions else 'Not provided'}
    
    Industry Use Cases:
    {chr(10).join(use_cases) if use_cases else 'Not provided'}
    """
    
    # Generate deck using AI
    chat = LlmChat(
        api_key=os.environ['EMERGENT_LLM_KEY'],
        session_id=f"deck_{request.lead_id}",
        system_message="You are an expert sales presentation creator. Generate compelling, professional sales deck content in JSON format."
    ).with_model("openai", "gpt-4o")
    
    prompt = f"""
    Based on the following context, create a comprehensive B2B SaaS sales presentation with 8-10 slides.
    
    {context}
    
    Return ONLY a JSON object with this exact structure (no markdown, no code blocks):
    {{
        "title": "Presentation title",
        "slides": [
            {{
                "type": "title",
                "title": "Main title",
                "subtitle": "Tagline"
            }},
            {{
                "type": "problem",
                "title": "The Challenge",
                "points": ["point 1", "point 2", "point 3"]
            }},
            {{
                "type": "solution",
                "title": "Our Solution",
                "description": "Solution overview",
                "points": ["benefit 1", "benefit 2", "benefit 3"]
            }},
            {{
                "type": "features",
                "title": "Key Features",
                "features": [
                    {{"name": "Feature 1", "description": "Description"}},
                    {{"name": "Feature 2", "description": "Description"}}
                ]
            }},
            {{
                "type": "use_case",
                "title": "Industry Application",
                "description": "How it applies to their industry"
            }},
            {{
                "type": "roi",
                "title": "Value Proposition",
                "metrics": [
                    {{"label": "Time Saved", "value": "10-15 hours/week"}},
                    {{"label": "Efficiency", "value": "300% increase"}}
                ]
            }},
            {{
                "type": "cta",
                "title": "Next Steps",
                "description": "Call to action",
                "action": "Schedule a demo"
            }}
        ]
    }}
    """
    
    message = UserMessage(text=prompt)
    response = await chat.send_message(message)
    
    # Parse AI response
    try:
        # Clean response - remove markdown code blocks if present
        clean_response = response.strip()
        if clean_response.startswith('```'):
            clean_response = clean_response.split('\n', 1)[1]
            if clean_response.endswith('```'):
                clean_response = clean_response.rsplit('\n', 1)[0]
        
        deck_content = json.loads(clean_response)
    except json.JSONDecodeError:
        # Fallback deck structure
        deck_content = {
            "title": f"Sales Presentation for {client['name']}",
            "slides": [
                {"type": "title", "title": f"Partnership Proposal for {client['name']}", "subtitle": "Transform Your Business"}
            ]
        }
    
    # Save deck
    deck = SalesDeck(
        user_id=current_user.id,
        lead_id=request.lead_id,
        lead_name=lead['client_name'],
        content=deck_content
    )
    
    deck_dict = deck.model_dump()
    deck_dict['created_at'] = deck_dict['created_at'].isoformat()
    
    await db.sales_decks.insert_one(deck_dict)
    return deck

@api_router.get("/decks", response_model=List[SalesDeck])
async def get_decks(current_user: User = Depends(get_current_user)):
    decks = await db.sales_decks.find({"user_id": current_user.id}, {"_id": 0}).to_list(1000)
    
    for deck in decks:
        if isinstance(deck['created_at'], str):
            deck['created_at'] = datetime.fromisoformat(deck['created_at'])
    
    return decks

@api_router.get("/decks/{deck_id}", response_model=SalesDeck)
async def get_deck(deck_id: str, current_user: User = Depends(get_current_user)):
    deck = await db.sales_decks.find_one({"id": deck_id, "user_id": current_user.id}, {"_id": 0})
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    if isinstance(deck['created_at'], str):
        deck['created_at'] = datetime.fromisoformat(deck['created_at'])
    
    return SalesDeck(**deck)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()