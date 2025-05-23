from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from database import get_database, startup_db_client, shutdown_db_client
from models import AIAssistant, AIAssistantCreate, AIAssistantUpdate
from typing import List, Optional
import uvicorn
from contextlib import asynccontextmanager
import secrets
import os
from datetime import datetime

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Protocol for application startup and shutdown"""
    # Запуск подключения к БД
    await startup_db_client()
    yield
    # Завершение работы с БД
    await shutdown_db_client()

app = FastAPI(title="AI Assistants Management System", version="2.0.0", lifespan=lifespan)

# Настройки безопасности
security = HTTPBasic()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD",)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_projects_collection():
    db = await get_database()
    return db.projects

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Проверка учетных данных администратора"""
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"), ADMIN_USERNAME.encode("utf8")
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"), ADMIN_PASSWORD.encode("utf8")
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/")
async def root():
    return {"message": "AI Assistants Management System API", "version": "2.0.0"}

# API для фронтенда
@app.get("/api/projects", response_model=List[AIAssistant])
async def get_projects(
    category: Optional[str] = None,
    status: Optional[str] = None,
    collection=Depends(get_projects_collection)
):
    """Получить все проекты с возможностью фильтрации"""
    filter_query = {}
    
    if category:
        filter_query["category"] = category
    if status:
        filter_query["status"] = status
    
    projects = await collection.find(filter_query).to_list(length=None)
    
    for project in projects:
        project["id"] = str(project["_id"])
        del project["_id"]
    
    return projects

@app.get("/api/projects/{project_id}", response_model=AIAssistant)
async def get_project(project_id: str, collection=Depends(get_projects_collection)):
    """Получить проект по ID"""
    from bson import ObjectId
    
    try:
        project = await collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project["id"] = str(project["_id"])
        del project["_id"]
        return project
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid project ID")

@app.post("/api/projects", response_model=AIAssistant)
async def create_project(
    project: AIAssistantCreate, 
    collection=Depends(get_projects_collection),
    admin=Depends(verify_admin)
):
    """Создать новый проект (требует аутентификации)"""
    project_dict = project.model_dump()
    
    if not project_dict.get("links") or len(project_dict["links"]) == 0:
        raise HTTPException(status_code=400, detail="At least one link is required")
    
    # Добавляем временные метки
    project_dict["created_at"] = datetime.utcnow()
    project_dict["updated_at"] = datetime.utcnow()
    
    result = await collection.insert_one(project_dict)
    
    created_project = await collection.find_one({"_id": result.inserted_id})
    created_project["id"] = str(created_project["_id"])
    del created_project["_id"]
    
    return created_project

@app.put("/api/projects/{project_id}", response_model=AIAssistant)
async def update_project(
    project_id: str,
    project_update: AIAssistantUpdate,
    collection=Depends(get_projects_collection),
    admin=Depends(verify_admin)
):
    """Обновить проект (требует аутентификации)"""
    from bson import ObjectId
    
    try:
        update_dict = {k: v for k, v in project_update.model_dump().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Обновляем временную метку
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": update_dict}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        
        updated_project = await collection.find_one({"_id": ObjectId(project_id)})
        updated_project["id"] = str(updated_project["_id"])
        del updated_project["_id"]
        
        return updated_project
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid project ID or update data")

@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: str, 
    collection=Depends(get_projects_collection),
    admin=Depends(verify_admin)
):
    """Удалить проект (требует аутентификации)"""
    from bson import ObjectId
    
    try:
        result = await collection.delete_one({"_id": ObjectId(project_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"message": "Project deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid project ID")

@app.get("/api/categories")
async def get_categories(collection=Depends(get_projects_collection)):
    """Получить все уникальные категории"""
    categories = await collection.distinct("category")
    return {"categories": [cat for cat in categories if cat]}

@app.get("/api/statuses")
async def get_statuses(collection=Depends(get_projects_collection)):
    """Получить все уникальные статусы"""
    statuses = await collection.distinct("status")
    return {"statuses": [status for status in statuses if status]}

@app.get("/api/stats")
async def get_stats(collection=Depends(get_projects_collection)):
    """Получить статистику проектов"""
    total = await collection.count_documents({})
    active = await collection.count_documents({"status": "Активен"})
    completed = await collection.count_documents({"is_project_completed": True})
    
    # Средний рейтинг
    pipeline = [
        {"$match": {"rating": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}}}
    ]
    rating_result = await collection.aggregate(pipeline).to_list(length=1)
    avg_rating = rating_result[0]["avg_rating"] if rating_result else 0
    
    return {
        "total_projects": total,
        "active_projects": active,
        "completed_projects": completed,
        "average_rating": round(avg_rating, 2)
    }

# Роуты для HTML страниц
@app.get("/", response_class=HTMLResponse)
async def home_page():
    """Главная страница"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/projects", response_class=HTMLResponse)
async def projects_page():
    """Главная страница с проектами"""
    with open("templates/projects.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """Страница администрирования"""
    with open("templates/admin.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
