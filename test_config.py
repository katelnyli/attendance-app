from app.core.config import settings

print("DB URI:", settings.SQLALCHEMY_DATABASE_URI)
print("Secret key loaded:", bool(settings.SECRET_KEY))
