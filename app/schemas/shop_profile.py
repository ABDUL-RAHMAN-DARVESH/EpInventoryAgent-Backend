from pydantic import BaseModel, Field


class ShopProfileUpdate(BaseModel):
    shop_name: str | None = Field(None, min_length=1, max_length=255)
    shop_address: str | None = Field(None, max_length=500)
    shop_phone: str | None = Field(None, max_length=50)
