from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from database.models import User, Channel
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
    return user_obj
