from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum

# Enums для валидации
class ProjectStatus(str, Enum):
    IN_DEVELOPMENT = "В разработке"
    IN_TESTING = "В тестировании"
    ACTIVE = "Активен"
    COMPLETED = "Завершен"
    PAUSED = "Приостановлен"
    CANCELLED = "Отменен"

class LinkType(str, Enum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    DEMO = "demo"
    WEBSITE = "website"
    API = "api"
    DOCUMENTATION = "documentation"
    GITHUB = "github"

# Модели
class ProjectLink(BaseModel):
    """Модель ссылки проекта"""
    name: str = Field(..., min_length=1, max_length=100, description="Название ссылки")
    url: str = Field(..., min_length=1, pattern=r'^https?://', description="URL ссылки (должен начинаться с http:// или https://)")
    type: Optional[LinkType] = Field(None, description="Тип ссылки")

    @field_validator('name', 'url')
    @classmethod
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Поле не может быть пустым')
        return v.strip()

class AIAssistantBase(BaseModel):
    """Базовая модель ИИ ассистента"""
    name: str = Field(..., min_length=1, max_length=200, description="Название проекта")
    admin_panel_name: Optional[str] = Field(None, max_length=200, description="Название в админке")
    project_description: str = Field(..., min_length=10, max_length=1000, description="Описание проекта")
    links: List[ProjectLink] = Field(..., min_items=1, description="Список ссылок проекта (минимум одна)")
    is_project_completed: bool = Field(False, description="Завершенный ли проект")
    status: ProjectStatus = Field(..., description="Статус проекта")
    features: Optional[List[str]] = Field(default_factory=list, description="Ключевые возможности")
    category: Optional[str] = Field(None, description="Категория проекта")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Рейтинг от 0 до 5")
    
    @field_validator('name', 'project_description')
    @classmethod
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Поле не может быть пустым')
        return v.strip()
    
    @field_validator('features')
    @classmethod
    def validate_features(cls, v):
        if v:
            return [f.strip() for f in v if f and f.strip()]
        return []
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v):
        if v and v.strip():
            return v.strip()
        return None

class AIAssistantCreate(AIAssistantBase):
    """Модель для создания ИИ ассистента"""
    pass

class AIAssistantUpdate(AIAssistantBase):
    """Модель для обновления ИИ ассистента"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    project_description: Optional[str] = Field(None, min_length=10, max_length=1000)
    links: Optional[List[ProjectLink]] = Field(None, min_items=1)
    is_project_completed: Optional[bool] = None
    status: Optional[ProjectStatus] = None

class AIAssistantResponse(AIAssistantBase):
    """Модель ответа ИИ ассистента"""
    id: str = Field(..., description="ID проекта")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    
    class Config:
        from_attributes = True

class ProjectStats(BaseModel):
    """Статистика проектов"""
    total_projects: int = Field(..., description="Общее количество проектов")
    active_projects: int = Field(..., description="Количество активных проектов")
    completed_projects: int = Field(..., description="Количество завершенных проектов")
    average_rating: Optional[float] = Field(None, description="Средний рейтинг")

class CategoriesResponse(BaseModel):
    """Список категорий"""
    categories: List[str] = Field(..., description="Список уникальных категорий")

class StatusesResponse(BaseModel):
    """Список статусов"""
    statuses: List[str] = Field(..., description="Список доступных статусов")