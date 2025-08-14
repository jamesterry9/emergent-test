from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
from datetime import datetime, timedelta
import jwt
from passlib.hash import bcrypt
import motor.motor_asyncio
from dotenv import load_dotenv
import asyncio
from emergentintegrations.llm.chat import LlmChat, UserMessage

# Load environment variables
load_dotenv()

app = FastAPI()

# Database setup
MONGO_URL = os.environ.get('MONGO_URL')
DATABASE_NAME = os.environ.get('DB_NAME', 'chatbot_app')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client[DATABASE_NAME]

# Collections
users_collection = db.users
chatbots_collection = db.chatbots
conversations_collection = db.conversations
messages_collection = db.messages

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
JWT_SECRET = "your-secret-key-here"
JWT_ALGORITHM = "HS256"

# Pydantic models
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class ChatbotCreate(BaseModel):
    name: str
    description: str
    introduction: str
    is_censored: bool = True

class ChatbotUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    introduction: Optional[str] = None
    is_censored: Optional[bool] = None

class ChatMessage(BaseModel):
    message: str

class User(BaseModel):
    id: str
    username: str
    created_at: datetime

class Chatbot(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    introduction: str
    is_censored: bool
    created_at: datetime
    creator_username: str

class Conversation(BaseModel):
    id: str
    user_id: str
    chatbot_id: str
    created_at: datetime

class Message(BaseModel):
    id: str
    conversation_id: str
    sender_type: str  # 'user' or 'chatbot'
    content: str
    timestamp: datetime

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await users_collection.find_one({"username": username})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(
            id=user["id"],
            username=user["username"],
            created_at=user["created_at"]
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Auth endpoints
@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    # Check if username already exists
    existing_user = await users_collection.find_one({"username": user_data.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Hash password
    hashed_password = bcrypt.hash(user_data.password)
    
    # Create user
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "username": user_data.username,
        "password_hash": hashed_password,
        "created_at": datetime.utcnow()
    }
    
    await users_collection.insert_one(user_doc)
    
    # Create access token
    access_token = create_access_token(data={"sub": user_data.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "username": user_data.username
        }
    }

@app.post("/api/auth/login")
async def login(user_data: UserLogin):
    user = await users_collection.find_one({"username": user_data.username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not bcrypt.verify(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user_data.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"]
        }
    }

@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# Chatbot endpoints
@app.post("/api/chatbots", response_model=Chatbot)
async def create_chatbot(chatbot_data: ChatbotCreate, current_user: User = Depends(get_current_user)):
    chatbot_id = str(uuid.uuid4())
    chatbot_doc = {
        "id": chatbot_id,
        "user_id": current_user.id,
        "name": chatbot_data.name,
        "description": chatbot_data.description,
        "introduction": chatbot_data.introduction,
        "is_censored": chatbot_data.is_censored,
        "created_at": datetime.utcnow(),
        "creator_username": current_user.username
    }
    
    await chatbots_collection.insert_one(chatbot_doc)
    
    return Chatbot(**chatbot_doc)

@app.get("/api/chatbots", response_model=List[Chatbot])
async def get_all_chatbots():
    cursor = chatbots_collection.find({}).sort("created_at", -1)
    chatbots = []
    async for chatbot in cursor:
        chatbots.append(Chatbot(**chatbot))
    return chatbots

@app.get("/api/chatbots/my", response_model=List[Chatbot])
async def get_my_chatbots(current_user: User = Depends(get_current_user)):
    cursor = chatbots_collection.find({"user_id": current_user.id}).sort("created_at", -1)
    chatbots = []
    async for chatbot in cursor:
        chatbots.append(Chatbot(**chatbot))
    return chatbots

@app.get("/api/chatbots/{chatbot_id}", response_model=Chatbot)
async def get_chatbot(chatbot_id: str):
    chatbot = await chatbots_collection.find_one({"id": chatbot_id})
    if not chatbot:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    return Chatbot(**chatbot)

@app.put("/api/chatbots/{chatbot_id}", response_model=Chatbot)
async def update_chatbot(chatbot_id: str, chatbot_data: ChatbotUpdate, current_user: User = Depends(get_current_user)):
    chatbot = await chatbots_collection.find_one({"id": chatbot_id})
    if not chatbot:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    
    if chatbot["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this chatbot")
    
    update_data = {}
    for field, value in chatbot_data.dict(exclude_unset=True).items():
        update_data[field] = value
    
    if update_data:
        await chatbots_collection.update_one({"id": chatbot_id}, {"$set": update_data})
    
    updated_chatbot = await chatbots_collection.find_one({"id": chatbot_id})
    return Chatbot(**updated_chatbot)

@app.delete("/api/chatbots/{chatbot_id}")
async def delete_chatbot(chatbot_id: str, current_user: User = Depends(get_current_user)):
    chatbot = await chatbots_collection.find_one({"id": chatbot_id})
    if not chatbot:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    
    if chatbot["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this chatbot")
    
    await chatbots_collection.delete_one({"id": chatbot_id})
    await conversations_collection.delete_many({"chatbot_id": chatbot_id})
    await messages_collection.delete_many({"conversation_id": {"$in": []}})  # Clean up messages later
    
    return {"message": "Chatbot deleted successfully"}

# Chat endpoints
@app.post("/api/chat/{chatbot_id}/start", response_model=Conversation)
async def start_conversation(chatbot_id: str, current_user: User = Depends(get_current_user)):
    chatbot = await chatbots_collection.find_one({"id": chatbot_id})
    if not chatbot:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    
    conversation_id = str(uuid.uuid4())
    conversation_doc = {
        "id": conversation_id,
        "user_id": current_user.id,
        "chatbot_id": chatbot_id,
        "created_at": datetime.utcnow()
    }
    
    await conversations_collection.insert_one(conversation_doc)
    
    return Conversation(**conversation_doc)

@app.post("/api/chat/{conversation_id}/message")
async def send_message(conversation_id: str, message_data: ChatMessage, current_user: User = Depends(get_current_user)):
    conversation = await conversations_collection.find_one({"id": conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    chatbot = await chatbots_collection.find_one({"id": conversation["chatbot_id"]})
    if not chatbot:
        raise HTTPException(status_code=404, detail="Chatbot not found")
    
    # Save user message
    user_message_id = str(uuid.uuid4())
    user_message_doc = {
        "id": user_message_id,
        "conversation_id": conversation_id,
        "sender_type": "user",
        "content": message_data.message,
        "timestamp": datetime.utcnow()
    }
    await messages_collection.insert_one(user_message_doc)
    
    try:
        # Generate chatbot response using emergentintegrations
        system_message = f"{chatbot['introduction']} You are {chatbot['name']}. {chatbot['description']}"
        if not chatbot['is_censored']:
            system_message += " You can engage in roleplay and adult content as requested."
        else:
            system_message += " Keep your responses appropriate and family-friendly."
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=conversation_id,
            system_message=system_message
        ).with_model("openai", "gpt-4o-mini")
        
        user_message = UserMessage(text=message_data.message)
        response = await chat.send_message(user_message)
        
        # Save chatbot response
        bot_message_id = str(uuid.uuid4())
        bot_message_doc = {
            "id": bot_message_id,
            "conversation_id": conversation_id,
            "sender_type": "chatbot",
            "content": response,
            "timestamp": datetime.utcnow()
        }
        await messages_collection.insert_one(bot_message_doc)
        
        return {
            "user_message": Message(**user_message_doc),
            "bot_response": Message(**bot_message_doc)
        }
    
    except Exception as e:
        # If AI fails, return a fallback response
        bot_message_id = str(uuid.uuid4())
        bot_message_doc = {
            "id": bot_message_id,
            "conversation_id": conversation_id,
            "sender_type": "chatbot",
            "content": f"I'm sorry, I'm having trouble responding right now. Please try again later. ({str(e)[:50]}...)",
            "timestamp": datetime.utcnow()
        }
        await messages_collection.insert_one(bot_message_doc)
        
        return {
            "user_message": Message(**user_message_doc),
            "bot_response": Message(**bot_message_doc)
        }

@app.get("/api/chat/{conversation_id}/messages", response_model=List[Message])
async def get_conversation_messages(conversation_id: str, current_user: User = Depends(get_current_user)):
    conversation = await conversations_collection.find_one({"id": conversation_id})
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conversation["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    cursor = messages_collection.find({"conversation_id": conversation_id}).sort("timestamp", 1)
    messages = []
    async for message in cursor:
        messages.append(Message(**message))
    return messages

@app.get("/api/conversations", response_model=List[Conversation])
async def get_user_conversations(current_user: User = Depends(get_current_user)):
    cursor = conversations_collection.find({"user_id": current_user.id}).sort("created_at", -1)
    conversations = []
    async for conversation in cursor:
        conversations.append(Conversation(**conversation))
    return conversations

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)