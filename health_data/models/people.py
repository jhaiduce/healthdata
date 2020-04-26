from sqlalchemy import (
    Column,
    Index,
    Integer,
    String,
    Text,
    Float,
    ForeignKey,
    Sequence,
    DateTime,
    Boolean,
    Interval
)
from sqlalchemy.orm import relationship

from .meta import Base

from .security import User

class Person(Base):
    __tablename__ = 'person'
    id = Column(Integer, Sequence('person_seq'), primary_key=True)
    name = Column(String(255))

    user_id = Column(Integer,ForeignKey('user.id'),name='fk_user_id')
