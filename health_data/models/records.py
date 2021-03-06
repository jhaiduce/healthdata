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

def subtime(datetime_str,time_str):
    from sqlalchemy.dialects import sqlite

    if datetime_str is None or time_str is None:
        return None

    inp_datetime=sqlite.DATETIME().result_processor(sqlite,sqlite.DATETIME())(datetime_str)
    inp_time=sqlite.TIME().result_processor(sqlite,sqlite.TIME())(time_str)

    result = inp_datetime - (datetime.combine(datetime.min,inp_time) - datetime.combine(datetime.min,time(0)))

    result_str=sqlite.DATETIME().bind_processor(sqlite)(result)

    return result_str

def get_time_from_datetime(datetime_str):
    from sqlalchemy.dialects import sqlite

    if datetime_str is None: return None

    inp_datetime=sqlite.DATETIME().result_processor(sqlite,sqlite.DATETIME())(datetime_str)
    result=inp_datetime.time()
    result_str=sqlite.TIME().bind_processor(sqlite)(result)
    return result_str

@sa.event.listens_for(sa.engine.Engine,'connect')
def register_functions(conn, connection_record):
    from sqlite3 import Connection as sqliteConnection
    import math
    if isinstance(conn,sqliteConnection):
        conn.create_function("cos", 1, math.cos)
        conn.create_function("sin", 1, math.sin)
        conn.create_function("acos", 1, math.acos)
        conn.create_function("atan2", 2, math.atan2)
        conn.create_function("subtime", 2, subtime)
        conn.create_function("time", 1, get_time_from_datetime)

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

    @property
    def total_flow(self):
        menstrual_cup_flow=object_session(self).query(
            func.sum(MenstrualCupFill.fill).label('fill')
        ).filter(
            MenstrualCupFill.removal_time.between(
                datetime.combine(self.date,time(3)),
                datetime.combine(self.date+timedelta(days=1),time(3)))
        ).one().fill

        if menstrual_cup_flow == None:
            menstrual_cup_flow = 0

        absorbent_flow_query=object_session(self).query(
            func.sum(AbsorbentWeights.difference).label('difference')
        ).filter(
            AbsorbentWeights.time_after.between(
                datetime.combine(self.date,time(3)),
                datetime.combine(self.date+timedelta(days=1),time(3)))
        )

        absorbent_flow=absorbent_flow_query.one().difference

        if absorbent_flow == None:
            absorbent_flow = 0

        return menstrual_cup_flow + absorbent_flow

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

    @hybrid_property
    def time_before_inferred(self):
        if self.time_before is not None:
            return self.time_before

        if self.time_after is None:
            return None

        last_entry=object_session(self).query(
            AbsorbentWeights
        ).filter(
            AbsorbentWeights.time_before<self.time_after
        ).order_by(
            AbsorbentWeights.time_after
        ).limit(1).first()

        if last_entry is not None:
            last_time_after=last_entry.time_after
        else:
            last_time_after=datetime.combine(
                self.time_after.date(),time(8)
            ) - timedelta(days=1)

        return max(last_time_after,datetime.combine(self.time_after.date(),time(8)))

    @hybrid_property
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

    @difference.expression
    def difference(cls):

        all_records=aliased(cls)

        weight_before=case(
            [
                (
                    cls.weight_before==None,
                    sa.select(
                        [func.avg(all_records.weight_before)]
                    ).where(all_records.garment_id==cls.garment_id).as_scalar()
                ),
            ],
            else_ = cls.weight_before
        )

        return cls.weight_after - weight_before

    @property
    def flow_rate(self):
        hours = (self.time_after-self.time_before_inferred).total_seconds()/3600
        return self.difference/hours

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
