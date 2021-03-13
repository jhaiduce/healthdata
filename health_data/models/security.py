from sqlalchemy import (
    Column,
    Index,
    Integer,
    String,
    Float,
    ForeignKey,
    Sequence,
    DateTime,
    Boolean,
    Interval
)
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import relationship
from datetime import datetime

from .meta import Base

import bcrypt
import pyotp

class User(Base):
    __tablename__ = 'user'
    __table_args__ = {'mysql_encrypted':'yes'}
    
    id = Column(Integer, Sequence('locationtype_seq'), primary_key=True)
    name = Column(String(255),unique=True)
    pwhash = Column(String(255))
    pw_timestamp = Column(DateTime)
    otp_secret_ = Column('otp_secret',String(32))
    last_otp_hash = Column(String(255))

    @property
    def otp_secret(self):

        if self.otp_secret_ is None:
            self.otp_secret_ = pyotp.random_base32()

        return self.otp_secret_

    def otp_uri(self):

        return pyotp.totp.TOTP(self.otp_secret).provisioning_uri(
            name=self.name, issuer_name = 'healthdata')

    def check_otp(self,otp):

        if(
                # Check OTP is correct
                otp==pyotp.TOTP(self.otp_secret).now()

                # Protect against OTP reuse
                and (self.last_otp_hash is None or
                     not
                    bcrypt.checkpw(
                    otp.encode('utf8'),self.last_otp_hash.encode('utf8')))):

            self.last_otp_hash = bcrypt.hashpw(
                otp.encode('utf8'), bcrypt.gensalt()
            ).decode('utf8')

            return True

        return False

    def check_password(self,pw):
        return bcrypt.checkpw(pw.encode('utf8'), self.pwhash.encode('utf8'))

    def set_password(self,pw):

        self.pwhash = bcrypt.hashpw(
            pw.encode('utf8'), bcrypt.gensalt()
        ).decode('utf-8')

        self.pw_timestamp=datetime.now()
