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

class ProjectCategory(str, Enum):
    BUSINESS_AUTOMATION = "Бизнес-Автоматизация"
    SALES = "Продажи"
    CUSTOMER_SUPPORT = "Поддержка клиентов"
    ECOMMERCE = "E-commerce"
    EDUCATION = "Образование"
    HEALTHCARE = "Здравоохранение"
    FINANCE = "Финансы"
    REAL_ESTATE = "Недвижимость"
    OTHER = "Другое"

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
    category: Optional[ProjectCategory] = Field(None, description="Категория проекта")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Рейтинг от 0 до 5")
    
    @field_validator('name', 'project_description')
    @classmethod
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Поле не может быть пустым')
        return v.strip()
    
    @field_validator('features', mode='before')
    @classmethod
    def clean_features(cls, v):
        if v is None:
            return []
        # Фильтруем пустые строки
        return [f.strip() for f in v if f and f.strip()]
    
    @field_validator('admin_panel_name')
    @classmethod
    def clean_admin_name(cls, v):
        if v:
            return v.strip()
        return v

class AIAssistantCreate(AIAssistantBase):
    """Модель для создания ИИ ассистента"""
    pass

class AIAssistantUpdate(BaseModel):
    """Модель для обновления ИИ ассистента"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    admin_panel_name: Optional[str] = Field(None, max_length=200)
    project_description: Optional[str] = Field(None, min_length=10, max_length=1000)
    links: Optional[List[ProjectLink]] = Field(None, min_items=1)
    is_project_completed: Optional[bool] = None
    status: Optional[ProjectStatus] = None
    features: Optional[List[str]] = None
    category: Optional[ProjectCategory] = None
    rating: Optional[float] = Field(None, ge=0, le=5)
    
    @field_validator('name', 'project_description', 'admin_panel_name')
    @classmethod
    def validate_not_empty_if_provided(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Поле не может быть пустым')
        return v.strip() if v else v
    
    @field_validator('features', mode='before')
    @classmethod
    def clean_features(cls, v):
        if v is None:
            return v
        return [f.strip() for f in v if f and f.strip()]

class AIAssistant(AIAssistantBase):
    """Полная модель ИИ ассистента с метаданными"""
    id: str = Field(..., description="Уникальный идентификатор")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Дата создания")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Дата последнего обновления")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "Megastandart Assistant",
                "admin_panel_name": "megastandart",
                "project_description": "AI ассистент для обработки запросов клиентов компании Megastandart",
                "links": [
                    {
                        "name": "WhatsApp",
                        "url": "https://wa.me/77084368211",
                        "type": "whatsapp"
                    }
                ],
                "is_project_completed": True,
                "status": "Активен",
                "features": ["Обработка запросов", "Планирование встреч"],
                "category": "Бизнес-Автоматизация",
                "rating": 4.8,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }

# Статистика
class ProjectStats(BaseModel):
    """Модель статистики проектов"""
    total_projects: int = Field(..., description="Общее количество проектов")
    active_projects: int = Field(..., description="Количество активных проектов")
    completed_projects: int = Field(..., description="Количество завершенных проектов")
    average_rating: float = Field(..., description="Средний рейтинг проектов")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_projects": 10,
                "active_projects": 5,
                "completed_projects": 3,
                "average_rating": 4.2
            }
        }

# Для обратной совместимости
PROJECT_STATUSES = [status.value for status in ProjectStatus]
PROJECT_CATEGORIES = [category.value for category in ProjectCategory]
LINK_TYPES = [link_type.value for link_type in LinkType]