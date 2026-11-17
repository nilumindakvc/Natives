"""Category schemas (shared shape for product & service, major & sub)."""
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MajorCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: Optional[str] = Field(default=None, max_length=140)
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True


class MajorCategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    slug: Optional[str] = Field(default=None, max_length=140)
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class MajorCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: Optional[str]
    image_url: Optional[str]
    is_active: bool


class SubCategoryCreate(BaseModel):
    major_id: uuid.UUID
    name: str = Field(min_length=1, max_length=120)
    slug: Optional[str] = Field(default=None, max_length=140)
    description: Optional[str] = None
    is_active: bool = True


class SubCategoryUpdate(BaseModel):
    major_id: Optional[uuid.UUID] = None
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    slug: Optional[str] = Field(default=None, max_length=140)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SubCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    major_id: uuid.UUID
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
