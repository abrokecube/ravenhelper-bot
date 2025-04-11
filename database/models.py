from database import enums
from database.db import engine

from sqlalchemy import (
    Column, String, Integer, ForeignKey, Table, Enum, Boolean, DateTime, Float
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

class Base(AsyncAttrs, DeclarativeBase):
    pass

# Association table for many-to-many relationship
channel_alert = Table(
    'channel_alert',
    Base.metadata,
    Column('channel_name', String, ForeignKey('channels.name'), primary_key=True),
    Column('alert_id', Integer, ForeignKey('alerts.id'), primary_key=True)
)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    
    reminders = relationship("Reminder", back_populates='user')


class Channel(Base):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    alerts = relationship('Alert', secondary=channel_alert, back_populates='subscribers')
    reminders = relationship("Reminder", back_populates='channel')


class Alert(Base):
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Enum(enums.AlertType), nullable=False)

    subscribers = relationship('Channel', secondary=channel_alert, back_populates='alerts')


class Reminder(Base):
    __tablename__ = 'reminders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    
    user_id = Column(Integer, ForeignKey('users.id'))
    channel_id = Column(Integer, ForeignKey('channels.id'))
    
    user = relationship("User", back_populates='reminders')
    channel = relationship("Channel", back_populates='reminders')



async def create_all_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
