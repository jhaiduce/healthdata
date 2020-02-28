from sqlalchemy import (
    Column,
    Index,
    Integer,
    Text,
    String,
    DateTime,
    Float,
    ForeignKey,
    Sequence,
    Date
)

from sqlalchemy.sql import func

from sqlalchemy.orm import relationship


from .meta import Base

from datetime import datetime

class Record(Base):

    __tablename__='record'
    id = Column(Integer, Sequence('record_seq'), primary_key=True)
    entry_date = Column(DateTime, server_default=func.now())
    modified_date = Column(DateTime, onupdate=func.now())
    person = Column(Integer, ForeignKey('user.id',name='fk_user_id'))
    record_type = Column(String(255))

    __mapper_args__ = {
        'polymorphic_on':record_type,
        'polymorphic_identity':'record'
    }

class Note(Record):
    __tablename__ = 'note'
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    date = Column(DateTime)
    text = Column(Text)

    __mapper_args__ = {
        'polymorphic_identity':'note'
    }

class Temperature(Record):
    __tablename__ = 'temperature'
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    time = Column(DateTime)
    utcoffset = Column(Integer)
    temperature = Column(Float)

    __mapper_args__ = {
        'polymorphic_identity':'temperature'
    }

class Weight(Record):
    __tablename__ = 'weight'
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    time = Column(DateTime)
    utcoffset = Column(Integer)
    weight = Column(Float)

    __mapper_args__ = {
        'polymorphic_identity':'weight'
    }

class SymptomType(Base):
    __tablename__ = 'symptomtype'
    id = Column(Integer,Sequence('symptomtype_seq'), primary_key=True)
    entry_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, onupdate=datetime.utcnow)
    name = Column(String(255))

class Symptom(Record):
    __tablename__ = 'symptom'
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    symptomtype_id = Column(Integer,ForeignKey('symptomtype.id',name='fk_symtomtype_id'))
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    __mapper_args__ = {
        'polymorphic_identity':'symptom'
    }

class Period(Record):
    __tablename__ = 'period'
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    period_intensity = Column(Integer)
    cervical_fluid_character = Column(Integer)
    date = Column(Date)
    temperature_id=Column(Integer,ForeignKey('temperature.id'))
    notes_id=Column(Integer,ForeignKey('note.id'))

    temperature=relationship(Temperature,foreign_keys=temperature_id)

    notes=relationship(Note,foreign_keys=notes_id)

    __mapper_args__ = {
        'polymorphic_identity':'period'
    }

period_intensity_choices={
    1:'None',
    2:'.',
    3:'-',
    4:'+',
    5:'*',
    6:'#'
}

cervical_fluid_choices={
    1:'None',
    2:'Sticky',
    3:'Creamy',
    4:'Eggwhite'
}

