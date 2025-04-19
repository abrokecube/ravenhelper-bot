from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from database.models import User, Channel, BotSettings
from typing import Union
from twitchio import PartialUser
from sqlalchemy import select


async def get_user(
    session: AsyncSession,
    *, 
    user: PartialUser = None, 
    id: Union[int, str] = None,
    name: str = None
):
    if user is not None:
        id = user.id
        name = user.name
    
    if isinstance(id, str):
        id = int(id)
    
    if id:
        result = await session.execute(
            select(User).where(User.id == id)
        )
    elif name:
        result = await session.execute(
            select(User).where(User.name == name)
        )
    else:
        return None
    
    user_obj = result.scalar_one_or_none()
    if user_obj is None:
        user_obj = User(
            id=id,
            name=name
        )
        session.add(user_obj)
    return user_obj

async def get_channel(
    session: AsyncSession,
    *, 
    channel: PartialUser = None,
    id: Union[int, str] = None,
    name: str = None
):
    if channel is not None:
        id = channel.id
        name = channel.name
    
    if isinstance(id, str):
        id = int(id)
    
    if id:
        result = await session.execute(
            select(Channel).where(Channel.id == id)
        )
    elif name:
        result = await session.execute(
            select(Channel).where(Channel.name == name)
        )
    else:
        return None
    
    user_obj = result.scalar_one_or_none()
    if user_obj is None:
        user_obj = Channel(
            id=id,
            name=name
        )
        session.add(user_obj)
    if user_obj.name is None:
        user_obj.name = name
    return user_obj

async def get_channel_settings(
    session: AsyncSession,
    *, 
    channel: PartialUser = None,
    id: Union[int, str] = None,
    name: str = None
):
    if channel is not None:
        id = channel.id
        name = channel.name
    
    if isinstance(id, str):
        id = int(id)
    
    channel_obj = await get_channel(session, channel=channel, id=id, name=name)
    if channel_obj is None:
        return None
    
    result = await session.execute(
        select(BotSettings).where(BotSettings.channel_id == channel_obj.id)
    )
    
    settings_obj = result.scalar_one_or_none()
    if settings_obj is None:
        settings_obj = BotSettings(
            channel_id = channel_obj.id
        )
        session.add(settings_obj)
        await session.flush()
    return settings_obj
