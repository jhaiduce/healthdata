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
    Date,
    Boolean
)

from sqlalchemy.sql import func

from sqlalchemy.orm import relationship

from sqlalchemy.ext.declarative import declared_attr

from .meta import Base

from datetime import datetime

class Record(Base):

    __tablename__='record'
    __table_args__ = {'mysql_encrypted':'yes'}

    id = Column(Integer, Sequence('record_seq'), primary_key=True)
    record_type = Column(String(255))

    __mapper_args__ = {
        'polymorphic_on':record_type,
        'polymorphic_identity':'record'
    }

class TimestampedRecord(object):
    entry_date = Column(DateTime, server_default=func.now())
    modified_date = Column(DateTime, server_default=func.now(),
                           onupdate=func.now())

class IndividualRecord(object):

    @declared_attr
    def person_id(cls):
        return Column(Integer, ForeignKey(
            'person.id',
            name='fk_{}_person_id'.format(cls.__tablename__)))

    @declared_attr
    def person(cls):
        return relationship('Person')

import deform

class Note(TimestampedRecord,Record):
    __tablename__ = 'note'
    __table_args__ = {'mysql_encrypted':'yes'}

    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    date = Column(DateTime)
    text = Column(Text,info={'colanderalchemy':{'widget':deform.widget.TextAreaWidget()}})

    __mapper_args__ = {
        'polymorphic_identity':'note'
    }

class Temperature(TimestampedRecord,IndividualRecord,Record):
    __tablename__ = 'temperature'
    __table_args__ = {'mysql_encrypted':'yes'}

    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    time = Column(DateTime)
    utcoffset = Column(Integer)
    temperature = Column(Float)

    __mapper_args__ = {
        'polymorphic_identity':'temperature'
    }

class Weight(TimestampedRecord,IndividualRecord,Record):
    __tablename__ = 'weight'
    __table_args__ = {'mysql_encrypted':'yes'}

    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    time = Column(DateTime)
    utcoffset = Column(Integer)
    weight = Column(Float)

    __mapper_args__ = {
        'polymorphic_identity':'weight'
    }

class SymptomType(TimestampedRecord,Base):
    __tablename__ = 'symptomtype'
    __table_args__ = {'mysql_encrypted':'yes'}

    id = Column(Integer,Sequence('symptomtype_seq'), primary_key=True)
    name = Column(String(255))

class Symptom(TimestampedRecord,IndividualRecord,Record):
    __tablename__ = 'symptom'
    __table_args__ = {'mysql_encrypted':'yes'}

    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    symptomtype_id = Column(Integer,ForeignKey('symptomtype.id',name='fk_symtomtype_id'))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    notes_id=Column(Integer,ForeignKey('note.id'))

    symptomtype=relationship(SymptomType,foreign_keys=symptomtype_id)
    notes=relationship(Note,foreign_keys=notes_id)

    __mapper_args__ = {
        'polymorphic_identity':'symptom'
    }

class Period(TimestampedRecord,IndividualRecord,Record):
    __tablename__ = 'period'
    __table_args__ = {'mysql_encrypted':'yes'}

    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    period_intensity = Column(Integer)
    cervical_fluid_character = Column(Integer)
    date = Column(Date)
    temperature_id=Column(Integer,ForeignKey('temperature.id'))
    notes_id=Column(Integer,ForeignKey('note.id'))

    temperature=relationship(
        Temperature,foreign_keys=temperature_id,
        cascade='all, delete-orphan',
        single_parent=True)

    notes=relationship(Note,foreign_keys=notes_id)

    __mapper_args__ = {
        'polymorphic_identity':'period'
    }

class MenstrualCupFill(TimestampedRecord,IndividualRecord,Record):
    __tablename__ = 'menstrual_cup_fill'
    __table_args__ = {'mysql_encrypted':'yes'}

    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    time = Column(DateTime)
    fill = Column(Float)
    notes_id=Column(Integer,ForeignKey('note.id'))

    notes=relationship(Note,foreign_keys=notes_id)

    __mapper_args__ = {
        'polymorphic_identity':'menstrual_cup_fill'
    }

class AbsorbentGarment(Base):
    __tablename__='absorbent_garments'
    __table_args__ = {'mysql_encrypted':'yes'}

    id = Column(Integer, Sequence('absorbent_garment_seq'), primary_key=True)
    name = Column(String(255))

class AbsorbentWeights(TimestampedRecord,IndividualRecord,Record):
    __tablename__ = 'absorbent_weights'
    __table_args__ = {'mysql_encrypted':'yes'}

    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    time_before = Column(DateTime)
    time_after = Column(DateTime)
    garment_id = Column(Integer,ForeignKey('absorbent_garments.id'))
    weight_before = Column(Float)
    weight_after = Column(Float)
    blood_observed=Column(Boolean)
    notes_id=Column(Integer,ForeignKey('note.id'))

    notes=relationship(Note,foreign_keys=notes_id)
    garment=relationship(AbsorbentGarment,foreign_keys=garment_id)

    __mapper_args__ = {
        'polymorphic_identity':'absorbent_weights'
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
    2:'Sticky (light)',
    3:'Creamy (medium)',
    4:'Eggwhite (heavy)'
}
