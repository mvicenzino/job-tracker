from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class ChecklistItem(Base, TimestampMixin):
    """A checklist item for application preparation."""
    __tablename__ = 'checklist_items'

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    completed = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    application = relationship("Application", backref="checklist_items")

    def __repr__(self):
        return f"<ChecklistItem(id={self.id}, label='{self.label}', completed={self.completed})>"
