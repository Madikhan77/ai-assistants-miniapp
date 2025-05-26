import os
import logging
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import secrets

from models import (
    AIAssistantCreate, 
    AIAssistantUpdate, 
    AIAssistantResponse, 
    ProjectStats,
    CategoriesResponse,
    StatusesResponse,
    ProjectStatus
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Глобальные переменные для MongoDB
db_client: Optional[AsyncIOMotorClient] = None
db = None

# Конфигурация
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")
COLLECTION_NAME = "ai_assistants"
HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT"))

# Аутентификация
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

security = HTTPBasic()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    global db_client, db
    try:
        logger.info(f"Connecting to MongoDB at {MONGODB_URL}")
        db_client = AsyncIOMotorClient(MONGODB_URL)
        db = db_client[DATABASE_NAME]
        
        # Проверка подключения
        await db_client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB")
        
        # Создание индексов
        collection = db[COLLECTION_NAME]
        await collection.create_index("name")
        await collection.create_index("status")
        await collection.create_index("category")
        await collection.create_index("created_at")
        logger.info("✅ Database indexes created")
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise
    
    yield
    
    # Shutdown
    if db_client:
        db_client.close()
        logger.info("✅ MongoDB connection closed")

# Создание приложения
app = FastAPI(
    title="AI Assistants API",
    description="API for managing AI assistant projects",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Функция проверки аутентификации
def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Проверка учетных данных администратора"""
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"), 
        ADMIN_USERNAME.encode("utf8")
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"), 
        ADMIN_PASSWORD.encode("utf8")
    )
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username

# API Endpoints
@app.get("/api/projects", response_model=List[AIAssistantResponse])
async def get_projects(
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    completed: Optional[bool] = None
):
    """Получить список всех проектов с опциональной фильтрацией"""
    try:
        collection = db[COLLECTION_NAME]
        
        # Построение фильтра
        filter_query = {}
        if status_filter:
            filter_query["status"] = status_filter
        if category_filter:
            filter_query["category"] = category_filter
        if completed is not None:
            filter_query["is_project_completed"] = completed
        
        # Получение проектов
        cursor = collection.find(filter_query).sort("created_at", -1)
        projects = []
        
        async for project in cursor:
            project["id"] = str(project["_id"])
            projects.append(AIAssistantResponse(**project))
        
        logger.info(f"Retrieved {len(projects)} projects")
        return projects
        
    except Exception as e:
        logger.error(f"Error retrieving projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}", response_model=AIAssistantResponse)
async def get_project(project_id: str):
    """Получить конкретный проект по ID"""
    try:
        from bson import ObjectId
        
        collection = db[COLLECTION_NAME]
        project = await collection.find_one({"_id": ObjectId(project_id)})
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project["id"] = str(project["_id"])
        return AIAssistantResponse(**project)
        
    except Exception as e:
        logger.error(f"Error retrieving project: {e}")
        if "ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid project ID format")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects", response_model=AIAssistantResponse, status_code=201)
async def create_project(
    project: AIAssistantCreate,
    username: str = Depends(verify_credentials)
):
    """Создать новый проект (требует аутентификации)"""
    try:
        collection = db[COLLECTION_NAME]
        
        # Подготовка данных
        project_data = project.model_dump()
        project_data["created_at"] = datetime.utcnow()
        project_data["updated_at"] = datetime.utcnow()
        
        # Убираем рейтинг при создании
        project_data.pop("rating", None)
        
        # Создание проекта
        result = await collection.insert_one(project_data)
        
        # Получение созданного проекта
        created_project = await collection.find_one({"_id": result.inserted_id})
        created_project["id"] = str(created_project["_id"])
        
        logger.info(f"Project created by {username}: {project.name}")
        return AIAssistantResponse(**created_project)
        
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/projects/{project_id}", response_model=AIAssistantResponse)
async def update_project(
    project_id: str,
    project: AIAssistantUpdate,
    username: str = Depends(verify_credentials)
):
    """Обновить существующий проект (требует аутентификации)"""
    try:
        from bson import ObjectId
        
        collection = db[COLLECTION_NAME]
        
        # Проверка существования проекта
        existing = await collection.find_one({"_id": ObjectId(project_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Подготовка данных для обновления
        update_data = {k: v for k, v in project.model_dump().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        
        # Убираем рейтинг при обновлении
        update_data.pop("rating", None)
        
        # Обновление проекта
        await collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": update_data}
        )
        
        # Получение обновленного проекта
        updated_project = await collection.find_one({"_id": ObjectId(project_id)})
        updated_project["id"] = str(updated_project["_id"])
        
        logger.info(f"Project updated by {username}: {project_id}")
        return AIAssistantResponse(**updated_project)
        
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        if "ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid project ID format")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: str,
    username: str = Depends(verify_credentials)
):
    """Удалить проект (требует аутентификации)"""
    try:
        from bson import ObjectId
        
        collection = db[COLLECTION_NAME]
        
        # Удаление проекта
        result = await collection.delete_one({"_id": ObjectId(project_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        
        logger.info(f"Project deleted by {username}: {project_id}")
        return {"message": "Project successfully deleted"}
        
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        if "ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid project ID format")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats", response_model=ProjectStats)
async def get_stats():
    """Получить статистику проектов"""
    try:
        collection = db[COLLECTION_NAME]
        
        # Подсчет статистики
        total_projects = await collection.count_documents({})
        active_projects = await collection.count_documents({"status": "Активен"})
        completed_projects = await collection.count_documents({"is_project_completed": True})
        
        # Средний рейтинг (игнорируем, так как убрали рейтинги)
        average_rating = None
        
        return ProjectStats(
            total_projects=total_projects,
            active_projects=active_projects,
            completed_projects=completed_projects,
            average_rating=average_rating
        )
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/categories", response_model=CategoriesResponse)
async def get_categories():
    """Получить список всех уникальных категорий"""
    try:
        collection = db[COLLECTION_NAME]
        
        # Получение уникальных категорий
        categories = await collection.distinct("category")
        
        # Фильтрация пустых значений
        categories = [cat for cat in categories if cat]
        
        # Сортировка
        categories.sort()
        
        return CategoriesResponse(categories=categories)
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/statuses", response_model=StatusesResponse)
async def get_statuses():
    """Получить список всех доступных статусов"""
    try:
        # Возвращаем все статусы из enum
        statuses = [status.value for status in ProjectStatus]
        return StatusesResponse(statuses=statuses)
        
    except Exception as e:
        logger.error(f"Error getting statuses: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

# HTML страницы
@app.get("/")
async def root():
    """Перенаправление на страницу проектов"""
    return FileResponse("static/projects.html")

@app.get("/projects")
async def projects_page():
    """Страница с проектами"""
    return FileResponse("static/projects.html")

@app.get("/admin")
async def admin_page():
    """Админ панель"""
    return FileResponse("static/admin.html")

# Health check
@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    try:
        # Проверка подключения к БД
        await db_client.admin.command('ping')
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info"
    )