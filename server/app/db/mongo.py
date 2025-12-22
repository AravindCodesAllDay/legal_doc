import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.settings import settings

class MongoDB:
    client: AsyncIOMotorClient = None
    db_name: str = settings.MONGO_DB_NAME

db = MongoDB()

async def connect_to_mongo():
    logger = logging.getLogger("uvicorn")
    try:
        db.client = AsyncIOMotorClient(settings.MONGO_URI)
        await db.client.server_info()
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error(f"Could not connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    if db.client:
        db.client.close()
        logging.getLogger("uvicorn").info("Closed MongoDB connection")

async def get_db():
    if db.client is None:
        await connect_to_mongo()
    return db.client[db.db_name]
