from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import os
from datetime import datetime
from dotenv import load_dotenv
import logging

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройки подключения к MongoDB
MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def connect_to_mongo():
    """Подключение к MongoDB"""
    try:
        db.client = AsyncIOMotorClient(MONGODB_URL)
        db.database = db.client[DATABASE_NAME]
        
        # Проверка подключения
        await db.client.admin.command('ping')
        logger.info(f"Successfully connected to MongoDB")
        
        # Создание индексов
        await create_indexes()
        
        # Инициализация тестовых данных
        await init_sample_data()
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during MongoDB connection: {e}")
        raise e

async def close_mongo_connection():
    """Закрытие подключения к MongoDB"""
    if db.client:
        db.client.close()
        logger.info("Disconnected from MongoDB")

async def get_database():
    """Получение экземпляра базы данных"""
    if db.database is None:
        raise ConnectionError("Database connection not established")
    return db.database

async def create_indexes():
    """Создание индексов для коллекций"""
    if db.database is None:
        return
    
    try:
        projects_collection = db.database.projects
        
        # Создаем индексы для быстрого поиска
        await projects_collection.create_index("name")
        await projects_collection.create_index("category")
        await projects_collection.create_index("status")
        await projects_collection.create_index("is_project_completed")
        await projects_collection.create_index("created_at")
        await projects_collection.create_index("rating")
        
        # Составной индекс для сортировки
        await projects_collection.create_index([("status", 1), ("created_at", -1)])
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")

async def init_sample_data():
    """Инициализация тестовых данных"""
    if db.database is None:
        return
    
    projects_collection = db.database.projects
    
    # Проверяем, есть ли уже данные
    count = await projects_collection.count_documents({})
    if count > 0:
        logger.info(f"Database already contains {count} projects")
        return
    
    # Создаем тестовые данные
    sample_projects = [
        {
            "name": "Megastandart AI Assistant",
            "admin_panel_name": "megastandart",
            "project_description": "Интеллектуальный ассистент для автоматизации обработки клиентских запросов и планирования встреч для компании Megastandart",
            "links": [
                {
                    "name": "WhatsApp Business",
                    "url": "https://api.whatsapp.com/send/?phone=77084368211",
                    "type": "whatsapp"
                }
            ],
            "is_project_completed": True,
            "status": "Активен",
            "features": [
                "Обработка входящих запросов 24/7",
                "Интеллектуальная маршрутизация обращений",
                "Автоматическое планирование встреч",
                "Интеграция с CRM системой"
            ],
            "category": "Бизнес-Автоматизация", 
            "rating": 4.8,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Aroma Fusion Bot",
            "admin_panel_name": "aroma_fusion@dauykit.com",
            "project_description": "AI-консультант для персонализированного подбора парфюмерии и оформления заказов в Aroma Fusion",
            "links": [
                {
                    "name": "Telegram Bot",
                    "url": "https://t.me/aroma_fus_bot",
                    "type": "telegram"
                },
                {
                    "name": "Demo Version",
                    "url": "https://demo.aromafusion.ai",
                    "type": "demo"
                }
            ],
            "is_project_completed": False,
            "status": "В разработке",
            "features": [
                "Персонализированный подбор ароматов",
                "Каталог с умным поиском",
                "Оформление и отслеживание заказов",
                "Программа лояльности"
            ],
            "category": "Продажи",
            "rating": 3.5,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Asyl Dan Rice Expert",
            "admin_panel_name": "asyl-dane-trade@dauys.kit",
            "project_description": "Специализированный B2B ассистент для оптовых продаж риса и консультаций по продукции Asyl Dan",
            "links": [
                {
                    "name": "WhatsApp Business",
                    "url": "https://api.whatsapp.com/send/?phone=77019703300",
                    "type": "whatsapp"
                }
            ],
            "is_project_completed": True,
            "status": "В тестировании",
            "features": [
                "Консультации по сортам риса",
                "Расчет оптовых цен",
                "Планирование поставок",
                "Техническая документация"
            ],
            "category": "Бизнес-Автоматизация",
            "rating": 4.2,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "Smart Realty Assistant",
            "admin_panel_name": "business_real_estate@dauyskit.com",
            "project_description": "Виртуальный риелтор для презентации объектов недвижимости и организации показов",
            "links": [
                {
                    "name": "WhatsApp",
                    "url": "https://api.whatsapp.com/send/?phone=77066065886",
                    "type": "whatsapp"
                },
                {
                    "name": "Web Platform",
                    "url": "https://realty.assistant.kz",
                    "type": "website"
                }
            ],
            "is_project_completed": True,
            "status": "Активен",
            "features": [
                "3D туры по объектам",
                "Умный подбор по критериям",
                "Онлайн-запись на показы",
                "Ипотечный калькулятор"
            ],
            "category": "Недвижимость",
            "rating": 4.5,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "AutoDrive Sales Bot",
            "admin_panel_name": "business_cars@dauyskit.com",
            "project_description": "Интеллектуальный консультант для автосалона с функцией записи на тест-драйв",
            "links": [
                {
                    "name": "WhatsApp",
                    "url": "https://api.whatsapp.com/send/?phone=77066065886",
                    "type": "whatsapp"
                },
                {
                    "name": "Telegram",
                    "url": "https://t.me/autodrive_bot",
                    "type": "telegram"
                },
                {
                    "name": "API Documentation",
                    "url": "https://api.autodrive.kz/docs",
                    "type": "api"
                }
            ],
            "is_project_completed": True,
            "status": "Активен",
            "features": [
                "Детальная информация о моделях",
                "Сравнение автомобилей",
                "Запись на тест-драйв",
                "Расчет кредита и лизинга",
                "Trade-in оценка"
            ],
            "category": "Продажи",
            "rating": 4.7,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "HealthCare Advisor",
            "admin_panel_name": "healthcare@dauyskit.com",
            "project_description": "Медицинский ассистент для первичной консультации и записи к специалистам",
            "links": [
                {
                    "name": "Telegram Bot",
                    "url": "https://t.me/health_advisor_bot",
                    "type": "telegram"
                }
            ],
            "is_project_completed": False,
            "status": "В разработке",
            "features": [
                "Анализ симптомов",
                "Рекомендации специалистов",
                "Онлайн-запись к врачу",
                "Напоминания о приеме"
            ],
            "category": "Здравоохранение",
            "rating": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    result = await projects_collection.insert_many(sample_projects)
    logger.info(f"Inserted {len(result.inserted_ids)} sample projects")

# События для подключения/отключения от MongoDB
async def startup_db_client():
    """Запуск подключения к базе данных"""
    await connect_to_mongo()

async def shutdown_db_client():
    """Остановка подключения к базе данных"""
    await close_mongo_connection()