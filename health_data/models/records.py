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
    Boolean,
    case
)

import sqlalchemy as sa

from sqlalchemy.sql import func

from sqlalchemy.orm import relationship, object_session, validates, aliased

from sqlalchemy.ext.declarative import declared_attr

from sqlalchemy.ext.hybrid import hybrid_property

from .meta import Base

from datetime import datetime, time, timedelta

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
    insertion_time_ = Column('insertion_time',DateTime)
    removal_time = Column(DateTime)
    fill = Column(Float)
    notes_id=Column(Integer,ForeignKey('note.id'))

    notes=relationship(Note,foreign_keys=notes_id)

    def __init__(self,*args,insertion_time=None,**kwargs):
        super(MenstrualCupFill,self).__init__(*args,**kwargs)
        self.insertion_time=insertion_time

    @hybrid_property
    def insertion_time(self):

        if self.insertion_time_ is not None:
            return self.insertion_time_

        if self.removal_time is None:
            return None

        last_entry=object_session(self).query(
            MenstrualCupFill
        ).filter(
            MenstrualCupFill.insertion_time_<self.removal_time
        ).order_by(
            MenstrualCupFill.removal_time.desc()
        ).with_entities(
            MenstrualCupFill.removal_time
        ).limit(1).first()

        if last_entry is not None:
            last_removal_time=last_entry.removal_time
        else:
            last_removal_time=datetime.combine(
                self.removal_time.date(),time(8)
            ) - timedelta(days=1)

        return max(last_removal_time,datetime.combine(self.removal_time.date(),time(8)))

    @insertion_time.expression
    def insertion_time(cls):

        previous=aliased(cls)

        last_removal_time=sa.select([
            func.max(previous.removal_time,func.to_date(cls.removal_time)-1)
        ]).where(
            previous.removal_time<cls.removal_time
        ).order_by(previous.removal_time.desc()).limit(1).as_scalar()

        insertion_time=case(
            [
                (cls.insertion_time_==None,func.max(last_removal_time,func.to_date(cls.removal_time))),
            ], else_ = cls.insertion_time_
        )

        return insertion_time

    @insertion_time.setter
    def insertion_time(self,value):
        self.insertion_time_=value

    @insertion_time.update_expression
    def insertion_time(cls,value):
        return [(cls.insertion_time_,value)]

    @hybrid_property
    def flow_rate(self):
        hours=(self.removal_time-self.insertion_time).total_seconds()/3600
        return self.fill/hours

    @flow_rate.expression
    def flow_rate(self):

        return func.time_to_sec(
            func.timediff(cls.removal_time,cls.insertion_time))

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

    @property
    def difference(self):
        if self.weight_after is None:
            return None

        weight_before=self.weight_before
        if weight_before is None:
            session=object_session(self)
            weight_before=session.query(
                func.avg(AbsorbentWeights.weight_before).label('average')
            ).filter(
                AbsorbentWeights.garment_id==self.garment_id).one().average

        if weight_before is None:
            return None

        return self.weight_after-weight_before

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
