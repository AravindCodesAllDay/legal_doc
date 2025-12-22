import motor.motor_asyncio

from app.core.settings import settings


class MongoDB:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.MONGO_URI)
        self.db = self.client["legal_docs"]
        self.users_collection = self.db["users"]


mongodb = MongoDB()
