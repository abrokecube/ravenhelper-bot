from database import enums
from database.db import engine

from sqlalchemy import (
    Column, String, Integer, ForeignKey, Table, Enum, Boolean, DateTime, Float, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    
    reminders = relationship("Reminder", back_populates='user')


class Channel(Base):
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    prefix = Column(JSON, nullable=False, default=["?"])

    reminders = relationship("Reminder", back_populates='channel')
    alerts = relationship("Alert", back_populates='channel')
    settings = relationship("BotSettings", back_populates="channel", uselist=False)


class BotSettings(Base):
    __tablename__ = 'botsettings'
    
    channel_id = Column(Integer, ForeignKey('channels.id'), primary_key=True)
    
    prefix = Column(JSON, nullable=False, default=['?'])
    bot_joined = Column(Boolean, nullable=False, default=False)
    
    channel = relationship("Channel", back_populates='settings')


class Alert(Base):
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Enum(enums.AlertType), nullable=False)
    data = Column(JSON, nullable=True)
    to_chat = Column(Boolean, nullable=False)
    to_whisper = Column(Boolean, nullable=False)
    to_announce = Column(Boolean, nullable=False)

    channel_id = Column(Integer, ForeignKey('channels.id'))
    
    channel = relationship("Channel", back_populates='alerts')


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
