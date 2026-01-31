from sqlalchemy import Column, Integer, String, Text, ForeignKey, Date
from .base import Base, TimestampMixin


class WeeklyReflection(Base, TimestampMixin):
    """Weekly reflection journal entry for job search momentum."""
    __tablename__ = 'weekly_reflections'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    week_of = Column(Date, nullable=False)  # Monday of the week
    energy_level = Column(Integer)  # 1-5 scale
    momentum = Column(String(20))  # "gaining", "steady", "losing"
    wins = Column(Text)  # What went well
    challenges = Column(Text)  # What was hard
    next_week_goals = Column(Text)  # What to focus on

    def __repr__(self):
        return f"<WeeklyReflection(id={self.id}, week_of='{self.week_of}')>"
