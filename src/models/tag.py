from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


# Association table for many-to-many relationship between entities and tags
entity_tags = Table(
    'entity_tags',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), nullable=False),
    Column('entity_type', String(50), nullable=False),  # 'company', 'job', 'application', 'contact'
    Column('entity_id', Integer, nullable=False),
)


class Tag(Base, TimestampMixin):
    """Tags for categorizing and filtering entities."""
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    color = Column(String(7))  # Hex color code for UI
    description = Column(String(255))

    def __repr__(self):
        return f"<Tag(id={self.id}, name='{self.name}')>"
