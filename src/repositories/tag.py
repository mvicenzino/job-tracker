from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import delete
from .base import BaseRepository
from ..models import Tag, entity_tags


class TagRepository(BaseRepository[Tag]):
    """Repository for Tag operations."""

    def __init__(self, session: Session):
        super().__init__(session, Tag)

    def get_by_name(self, name: str) -> Optional[Tag]:
        """Get a tag by exact name."""
        return self.session.query(Tag).filter(Tag.name == name).first()

    def search_by_name(self, name: str) -> List[Tag]:
        """Search tags by name (case-insensitive partial match)."""
        return self.session.query(Tag).filter(
            Tag.name.ilike(f"%{name}%")
        ).all()

    def get_or_create(self, name: str, color: str = None) -> Tag:
        """Get an existing tag or create a new one."""
        tag = self.get_by_name(name)
        if not tag:
            tag = self.create(name=name, color=color)
        return tag

    def add_tag_to_entity(self, tag_id: int, entity_type: str, entity_id: int):
        """Add a tag to an entity."""
        stmt = entity_tags.insert().values(
            tag_id=tag_id,
            entity_type=entity_type,
            entity_id=entity_id
        )
        self.session.execute(stmt)
        self.session.flush()

    def remove_tag_from_entity(self, tag_id: int, entity_type: str, entity_id: int):
        """Remove a tag from an entity."""
        stmt = delete(entity_tags).where(
            entity_tags.c.tag_id == tag_id,
            entity_tags.c.entity_type == entity_type,
            entity_tags.c.entity_id == entity_id
        )
        self.session.execute(stmt)
        self.session.flush()

    def get_entity_tags(self, entity_type: str, entity_id: int) -> List[Tag]:
        """Get all tags for an entity."""
        tag_ids = self.session.query(entity_tags.c.tag_id).filter(
            entity_tags.c.entity_type == entity_type,
            entity_tags.c.entity_id == entity_id
        ).all()

        if not tag_ids:
            return []

        return self.session.query(Tag).filter(
            Tag.id.in_([t[0] for t in tag_ids])
        ).all()

    def get_entities_by_tag(self, tag_id: int, entity_type: str = None) -> List[tuple]:
        """Get all entities with a specific tag."""
        query = self.session.query(
            entity_tags.c.entity_type,
            entity_tags.c.entity_id
        ).filter(entity_tags.c.tag_id == tag_id)

        if entity_type:
            query = query.filter(entity_tags.c.entity_type == entity_type)

        return query.all()
