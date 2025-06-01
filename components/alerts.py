from enum import Enum
import twitchio
from twitchio.ext import commands
from twitchio import eventsub
import asyncio
from database.enums import AlertType
from utils import utils
from typing import Dict, List, Iterable
from dataclasses import dataclass
from async_lru import alru_cache
import logging

import os
from dotenv import load_dotenv
load_dotenv()
import hermes

from database import models
from database import utils as dbutils
from database.session import get_async_session
from sqlalchemy import select
from sqlalchemy.orm import joinedload

class NoLastMessageException(Exception):
    def __init__(self, *args):
        super().__init__(*args)

@dataclass
class Subscription:
    alert_type: AlertType
    channel_id: str
    user_id: str
    channel_display_name: str = None
    user_name: str = None
    whisper: bool = False
    chat: bool = True
    announce: bool = False
    id: int = None
    
    def __eq__(self, value):
        a = (self.alert_type, self.channel_id, self.user_id)
        b = (value.alert_type, value.channel_id, value.user_id)
        return a == b

    def to_model_obj(self):
        data = {'channel_id': self.channel_id}
        if self.alert_type in (AlertType.DESYNC,):
            data = None
        return models.Alert(
            type = self.alert_type,
            data = data,
            to_chat = self.chat,
            to_whisper = self.whisper,
            to_announce = self.announce,
            channel_id = self.user_id
        )
        
    @staticmethod
    def from_model_obj(obj: models.Alert):
        channel_id = None
        if not obj.type in (AlertType.DESYNC,):
            channel_id = obj.data['channel_id']
        return Subscription(
            alert_type = obj.type,
            channel_id = str(channel_id),
            user_id = str(obj.channel_id),
            user_name=obj.channel.name,
            whisper = obj.to_whisper,
            chat = obj.to_chat,
            announce = obj.to_announce,
            id=obj.id
        )

class TwitchAlerts(hermes.TwitchUserPubSub):
    def __init__(self, component: 'AlertCommands'):
        self.component = component
        super().__init__(os.getenv("USER_TOKEN"))
    
    async def event_started(self):
        asyncio.create_task(self.component.load_subscriptions_from_db())
    
    async def event_message_pinned(self, subscription, payload):
        print(f"📌 Pinned message in {subscription.channel_id} by {payload['pinned_by']['display_name']}: {payload['message']['content']['text']}")
        pinned_by = payload['pinned_by']['display_name']
        channel = await self.component.get_user(user_id=subscription.channel_id)
        channel_name = channel.display_name
        message_content = payload['message']['content']['text']
        notif_text = f"📌 @{pinned_by} pinned a message in #{channel_name}: {message_content}"
        await self.component.push_notification(
            AlertType.PINS, subscription.channel_id, notif_text, alert_id=payload['id']
        )
        
    async def event_message_unpinned(self, subscription, payload):
        print(f"📌  unpinned message in {subscription.channel_id}")
        channel = await self.component.get_user(user_id=subscription.channel_id)
        reply_text = f"📌 The message was unpinned."
        if payload['unpinned_by']:
            fallback_text = f"📌 @{payload['unpinned_by']['display_name']} unpinned a message in #{channel.display_name}"
        else:
            fallback_text = f"📌 A message was unpinned in #{channel.display_name}"
        await self.component.push_notification(
            AlertType.UNPINS, subscription.channel_id, reply_text,
            True, fallback_text, payload['id'], AlertType.PINS
        )
        
    async def event_poll_started(self, subscription, payload):
        poll = payload
        print(f"🗳️ Poll created in {subscription.channel_id} by {poll['owned_by']}: {poll['title']}")
        title = poll['title']
        duration = utils.format_seconds(poll['duration_seconds'], include_zero=False)
        choices = ' – '.join([
            # f"({idx+1}.) {x['title']}" 
            f"\"{x['title']}\"" 
            for idx, x in enumerate(poll['choices'])
        ])
        channel = await self.component.get_user(user_id=subscription.channel_id)
        notif_text = f"🗳️ @{channel.name} started a poll: \"{title}\" ✦ {choices}. Ends in {duration}."
        await self.component.push_notification(
            AlertType.POLLS, subscription.channel_id, notif_text, alert_id=payload['poll_id']
        )
        
    async def event_poll_completed(self, subscription, payload):
        poll = payload
        print(f"🗳️ Poll completed in {subscription.channel_id} by {poll['owned_by']}: {poll['title']}")
        title = poll['title']
        highest_votes = max(*[x['total_voters'] for x in poll['choices']])
        total_votes = poll['votes']['total']
        if total_votes > 0:
            choices = ' – '.join([
                # f"{'🏆 ' if x['total_voters'] == highest_votes else ''}({idx+1}.) {x['title']}: "
                f"{'🏆 ' if x['total_voters'] == highest_votes else ''}\"{x['title']}\": "
                f"{x['total_voters']/total_votes:.1%} ({x['total_voters']})"
                for idx, x in enumerate(poll['choices'])
            ])
        else:
            choices = ' – '.join([
                # f"{'🏆 ' if x['total_voters'] == highest_votes else ''}({idx+1}.) {x['title']}: "
                f"\"{x['title']}\": "
                f"0% (0)"
                for idx, x in enumerate(poll['choices'])
            ])
        channel = await self.component.get_user(user_id=subscription.channel_id)
        reply_text = f"🗳️ Poll results: {choices}."
        fallback_text = f"🗳️ Poll finished in @{channel.name}: \"{title}\" ✦ {choices}."
        await self.component.push_notification(
            AlertType.POLLS, subscription.channel_id, reply_text, True, fallback_text, payload['poll_id']
        )
    
    async def event_raid_started(self, subscription, payload):
        channel = await self.component.get_user(user_id=subscription.channel_id)
        notif_text = f"🏃 @{channel.name} started a raid to @{payload['target_display_name']}!"
        await self.component.push_notification(
            AlertType.RAIDS, subscription.channel_id, notif_text, alert_id=payload['id']
        )
    
    async def event_raid_cancelled(self, subscription, payload):
        channel = await self.component.get_user(user_id=subscription.channel_id)
        reply_text = "The raid was cancelled."
        fallback_text = f"🧍 @{channel.name} cancelled the raid to @{payload['target_display_name']}!"
        await self.component.push_notification(
            AlertType.RAIDS, subscription.channel_id, reply_text, True, fallback_text, payload['id']
        )
    
    async def event_raid_completed(self, subscription, payload):
        channel = await self.component.get_user(user_id=subscription.channel_id)
        reply_text = f"Raid succeeded with {utils.pl(payload['viewer_count'], 'viewers')}!"
        fallback_text = f"🏃 @{channel.name} raided @{payload['target_display_name']} with {utils.pl(payload['viewer_count'], 'viewers')}!"
        await self.component.push_notification(
            AlertType.RAIDS, subscription.channel_id, reply_text, True, fallback_text, payload['id']
        )
    
    async def event_prediction_started(self, subscription, payload):
        channel = await self.component.get_user(user_id=subscription.channel_id)
        choices = ' – '.join([
            # f"({idx+1}.) {x['title']}" 
            f"\"{x['title']}\"" 
            for idx, x in enumerate(payload['outcomes'])
        ])
        duration = utils.format_seconds(payload['prediction_window_seconds'], include_zero=False)
        notif_text = f"🔮 @{channel.name} started a prediction: \"{payload['title']}\" ✦ {choices}. Closes in {duration}."
        await self.component.push_notification(
            AlertType.PREDICTIONS, subscription.channel_id, notif_text, alert_id=payload['id']
        )
    
    async def event_prediction_locked(self, subscription, payload):
        channel = await self.component.get_user(user_id=subscription.channel_id)
        total_points = sum([x['total_points'] for x in payload['outcomes']])
        total_users = sum([x['total_users'] for x in payload['outcomes']])
        choices = ' – '.join([
            f"\"{x['title']}\": 1:{total_points/x['total_points']:.2f}, {x['total_users']:,} users, {x['total_points']:,} points" 
            for idx, x in enumerate(payload['outcomes'])
        ])
        reply_text = f"🔮 The prediction was locked: {choices}."
        fallback_text = f"🔮 @{channel.name} locked a prediction: \"{payload['title']}\" ✦ {choices}."
        await self.component.push_notification(
            AlertType.PREDICTIONS, subscription.channel_id, reply_text, True, fallback_text, payload['id']
        )
    
    async def event_prediction_resolved(self, subscription, payload):
        channel = await self.component.get_user(user_id=subscription.channel_id)
        total_points = sum([x['total_points'] for x in payload['outcomes']])
        total_users = sum([x['total_users'] for x in payload['outcomes']])
        
        winner: hermes.PredictionOutcome = None
        for x in payload['outcomes']:
            if x['top_predictors'][0]['result']['type'] == "WIN":
                winner = x
                break

        choices = ' – '.join([
            f"{'🏆 ' if x == winner else ''}"
            f"\"{x['title']}\": 1:{total_points/x['total_points']:.2f}, "
            f"{x['total_users']:,} users, {x['total_points']:,} points" 
            for idx, x in enumerate(payload['outcomes'])
        ])
        reply_text = f"🔮 The final outcome was \"{winner['title']}\". {total_points:,} points will go to {winner['total_users']:,} users."
        fallback_text = f"🔮 @{channel.name} resolved a prediction: \"{payload['title']}\" ✦ {choices}. {total_points:,} points will go to {winner['total_users']:,} users."
        await self.component.push_notification(
            AlertType.PREDICTIONS, subscription.channel_id, reply_text, True, fallback_text, payload['id']
        )
    
    async def event_prediction_cancelled(self, subscription, payload):
        channel = await self.component.get_user(user_id=subscription.channel_id)
        total_points = sum([x['total_points'] for x in payload['outcomes']])
        total_users = sum([x['total_users'] for x in payload['outcomes']])
        
        choices = ' – '.join([
            f"\"{x['title']}\": 1:{total_points/x['total_points']:.2f}, {x['total_users']:,} users, {x['total_points']:,} points" 
            for idx, x in enumerate(payload['outcomes'])
        ])
        reply_text = f"🔮 The prediction was cancelled. {total_points:,} points will be refunded."
        fallback_text = f"🔮 @{channel.name} cancelled a prediction: \"{payload['title']}\" ✦ {choices}. {total_points:,} points will be refunded."
        await self.component.push_notification(
            AlertType.PREDICTIONS, subscription.channel_id, reply_text, True, fallback_text, payload['id']
        )
    async def event_channel_updated(self, subscription, payload):
        channel = await self.component.get_user(user_id=subscription.channel_id)
        if payload['old_status'] != payload['status']:
            text = f"📜 @{channel.display_name} changed title: \"{payload['status']}\""
            await self.component.push_notification(
                AlertType.TITLE, subscription.channel_id, text
            )
        if payload['old_game'] != payload['game']:
            text = f"🎮 @{channel.display_name} changed game: \"{payload['game']}\""
            await self.component.push_notification(
                AlertType.CATEGORY, subscription.channel_id, text
            )
        
        
class AlertCommands(commands.Component):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_alerts = TwitchAlerts(self)
        asyncio.create_task(self.user_alerts.run())
        self.subscriptions: Dict[AlertType, List[Subscription]] = {}
        self.twitch_subscriptions = set()
        self.channel_info: Dict[str, twitchio.ChannelInfo] = {}
        for x in AlertType:
            self.subscriptions[x] = []
    
    @alru_cache(maxsize=None)
    async def get_user(self, *, user_id: str = None, user_login: str = None) -> twitchio.User:
        if user_id:
            result = await self.bot.fetch_users(ids=[user_id])
        elif user_login:
            user_login = user_login.lstrip('@')
            result = await self.bot.fetch_users(logins=[user_login])
        else:
            return None
        if not result:
            return None
        else:
            return result[0]
    
    async def check_channel_alert(
        self, ctx: commands.Context, channel: str="", alerts: Iterable[str] = []
    ):
        if len(channel) == 0:
            await ctx.send("Please include a channel name.")
            return (None, None)
        channel = channel.lstrip("@")
        if not utils.is_twitch_username(channel):
            await ctx.send("uuh Not a valid user")
            return (None, None)
        channel_user_data = await self.get_user(user_login=channel)
        if not channel_user_data:
            await ctx.send("uuh Not a real user")
            return (None, None)
        valid_alerts = [x.value for x in AlertType]
        if len(alerts) == 0:
            await ctx.send(f"Specify one or more alert types. Available alerts: {', '.join(valid_alerts)}")
            return (None, None)
        for alert in alerts:
            if not alert.lower() in valid_alerts:
                await ctx.send(f"Invalid alert. Available alerts: {', '.join(valid_alerts)}")
                return (None, None)
        return channel, channel_user_data
        
    @commands.is_elevated()
    @commands.command(aliases=('notify','listen'))
    async def alert(self, ctx: commands.Context, channel: str="", *alerts: str):
        channel, channel_user_data = await self.check_channel_alert(ctx, channel, alerts)
        if channel is None:
            return
        successful_subs = []
        failed_subs = []
        missing_perm = False
        for alert in alerts:
            sub = Subscription(
                alert_type=AlertType(alert.lower()), 
                channel_id=channel_user_data.id,
                user_id=ctx.broadcaster.id,
                channel_display_name=channel_user_data.display_name,
                user_name=ctx.broadcaster.name,
            )
            if sub.alert_type in (AlertType.LIVE, AlertType.OFFLINE) and ctx.author.id != self.bot.owner_id:
                failed_subs.append(sub.alert_type.value)
                missing_perm = True
                continue
            if sub in self.subscriptions[sub.alert_type]:
                continue
                # await ctx.send(f"Already subscribed to this alert.")
                # return
            try:
                await self.add_subscription(sub)
            except twitchio.exceptions.HTTPException as e:
                failed_subs.append(sub.alert_type.value)
                logging.warning(f"(eventsub) Failed to subscribe to {alert} for {channel}: {e}")
                continue
            except (hermes.SubscriptionError, hermes.UnknownResponse) as e:
                failed_subs.append(sub.alert_type.value)
                logging.warning(f"(user) Failed to subscribe to {alert} for {channel}: {e}")
                continue
            await self.save_subscription_to_db(sub)
            successful_subs.append(sub.alert_type.value)
            
        if len(successful_subs) > 0:
            response_text = (
                f"Subscribed to {utils.strjoin(', ', *successful_subs, before_end=' and ')}"
                f" in #{sub.channel_display_name}."
            )
            if len(failed_subs) > 0:
                response_text += f" ({len(failed_subs)} failed.)"
        else:
            response_text = f"Failed to subscribe."
        await ctx.send(response_text)

    @commands.is_elevated()
    @commands.command(aliases=('unnotify','rmalert','removealert','unlisten'))
    async def delalert(self, ctx: commands.Context, channel: str="", *alerts: str):
        channel, channel_user_data = await self.check_channel_alert(ctx, channel, alerts)
        if channel is None:
            return
        successes = []
        for alert in alerts:
            alert_type = AlertType(alert.lower())
            subscription = None
            for sub in self.subscriptions[alert_type]:
                a = (sub.channel_id, sub.user_id)
                b = (channel_user_data.id, ctx.broadcaster.id)
                if a == b:
                    subscription = sub
                    break
            if subscription is None:
                continue
                # await ctx.send(f"No matching subscription found in this channel.")
                # return
            self.subscriptions[alert_type].remove(sub)
            await self.delete_subscription_from_db(subscription.id)
            successes.append(alert_type.value)
        if len(successes) == 0:
            await ctx.send(
                f"Failed to unsubscribe to alerts for #{channel_user_data.display_name}."
            )
            return
        await ctx.send(
            f"Unsubscribed to {utils.strjoin(', ', *successes, before_end=' and ')}"
            f" in #{channel_user_data.display_name}."
        )
    
    @commands.command(aliases=('listnotify','listlisten','listalerts'))
    async def listalert(self, ctx: commands.Context):
        alerts: Dict[str, List[AlertType]] = {}
        for alert_type in AlertType:
            for subs in self.subscriptions[alert_type]:
                if subs.user_id == ctx.broadcaster.id:
                    if subs.channel_display_name is None:
                        user = await self.get_user(user_id=subs.channel_id)
                        subs.channel_display_name = user.display_name
                    if not subs.channel_display_name in alerts:
                        alerts[subs.channel_display_name] = []
                    alerts[subs.channel_display_name].append(alert_type)
        channel_alert_strings = []
        alert_count = 0
        for channel, alert_types in alerts.items():
            channel_alert_strings.append(
                f"#{channel}: {utils.strjoin(', ', *[x.value for x in alert_types])}"
            )
            alert_count += len(alert_types)
        if alert_count == 0:
            await ctx.send(f"No subscribed alerts in {ctx.broadcaster.display_name}.")
            return
        await ctx.send(
            f"{utils.pl(alert_count, 'subscribed alerts')} in {ctx.broadcaster.display_name}: "
            f"{utils.strjoin(' – ', *channel_alert_strings)}."
        )

    async def subscribe_twitch(self, subscription: Subscription):
        eventsub_payload = None
        subscription_key = ""
        match subscription.alert_type:
            # case AlertType.TITLE | AlertType.CATEGORY:
            #     eventsub_payload = eventsub.ChannelUpdateSubscription(
            #         broadcaster_user_id = subscription.channel_id
            #     )
            #     channel_info = await self.bot.fetch_channels([subscription.channel_id])
            #     self.channel_info[subscription.channel_id] = channel_info[0]
            #     subscription_key = f"update_{subscription.channel_id}"
            case AlertType.LIVE:
                eventsub_payload = eventsub.StreamOnlineSubscription(
                    broadcaster_user_id = subscription.channel_id
                )
                subscription_key = f"online_{subscription.channel_id}"
            case AlertType.OFFLINE:
                eventsub_payload = eventsub.StreamOfflineSubscription(
                    broadcaster_user_id = subscription.channel_id
                )
                subscription_key = f"offline_{subscription.channel_id}"
        if subscription_key in self.twitch_subscriptions:
            return
        if eventsub_payload:
            await self.bot.subscribe_websocket(eventsub_payload)
            self.twitch_subscriptions.add(subscription_key)
            return
        pubsub_topic = None
        match subscription.alert_type:
            case AlertType.PINS | AlertType.UNPINS:
                pubsub_topic = hermes.SubTopic.PINS
                subscription_key = f"pins_{subscription.channel_id}"
            case AlertType.POLLS:
                pubsub_topic = hermes.SubTopic.POLLS
                subscription_key = f"polls_{subscription.channel_id}"
            case AlertType.RAIDS:
                pubsub_topic = hermes.SubTopic.RAIDS
                subscription_key = f"raids_{subscription.channel_id}"
            case AlertType.PREDICTIONS:
                pubsub_topic = hermes.SubTopic.PREDICTIONS
                subscription_key = f"predictions_{subscription.channel_id}"
            case AlertType.TITLE | AlertType.CATEGORY:
                pubsub_topic = hermes.SubTopic.BROADCAST_SETTINGS_UPDATE
                subscription_key = f"settings_{subscription.channel_id}"
        if subscription_key in self.twitch_subscriptions:
            return
        if pubsub_topic:
            await self.user_alerts.subscribe(pubsub_topic, subscription.channel_id)
            self.twitch_subscriptions.add(subscription_key)
        else:
            raise Exception(f"no mapped twitch subscription for {subscription.alert_type} aga")

    async def add_subscription(self, subscription: Subscription):
        await self.subscribe_twitch(subscription)
        self.subscriptions[subscription.alert_type].append(subscription)

    async def _send_notification_task(self, channel_id: str, text, reply_id, key: str):
        channel = self.bot.create_partialuser(channel_id)
        if reply_id is None:
            sent = await channel.send_message(sender=self.bot.user, token_for=self.bot.user, message=f"/me {text}", reply_to_message_id=reply_id)
        else:
            sent = await channel.send_message(sender=self.bot.user, token_for=self.bot.user, message=text, reply_to_message_id=reply_id)
        self._last_messages[key] = sent.id
    
    _last_messages = {}    
    # TODO: manage _last_messages better (potential memory leak)
    async def push_notification(
        self, alert_type: AlertType, channel_id: str, text: str, reply_to_last=False,
        reply_fallback_text: str = None, alert_id: str=None, related_alert_type: AlertType=None):
        for sub in self.subscriptions[alert_type]:
            if sub.channel_id == channel_id:
                key_alert = alert_type
                if related_alert_type is not None:
                    key_alert = related_alert_type
                key = f"{sub.user_id}_{key_alert.value}_{sub.channel_id}_{alert_id}"
                reply_id = None
                out_text = text
                if reply_to_last:
                    if key not in self._last_messages:
                        if reply_fallback_text is not None:
                            out_text = reply_fallback_text
                    else:
                        reply_id = self._last_messages[key]
                asyncio.create_task(self._send_notification_task(sub.user_id, out_text, reply_id, key))
    
    async def save_subscription_to_db(self, subscription: Subscription):
        async with get_async_session() as session:
            subscription_obj = subscription.to_model_obj()
            session.add(subscription_obj)
            await dbutils.get_channel(session, id=subscription.user_id, name=subscription.user_name)
            await session.flush()
            subscription.id = subscription_obj.id
    
    async def load_subscriptions_from_db(self):
        async with get_async_session() as session:
            result = await session.execute(
                select(models.Alert)
                .options(
                    joinedload(models.Alert.channel)
                )
            )
            alerts = result.scalars().all()
            for sub_obj in alerts:
                subs = Subscription.from_model_obj(sub_obj)
                asyncio.create_task(self.add_subscription(subs))
    
    async def delete_subscription_from_db(self, id: int):
        async with get_async_session() as session:
            result = await session.execute(
                select(models.Alert).where(models.Alert.id == id)
            )
            reminder_obj = result.scalar_one_or_none()
            if reminder_obj:
                await session.delete(reminder_obj)
    
    @commands.Component.listener()
    async def event_channel_update(self, payload: twitchio.ChannelUpdate):
        print(f"{payload.broadcaster.name} updated channel. Title: {payload.title}. Category: {payload.category_name}")
        old_channel_info = self.channel_info[payload.broadcaster.id]
        if payload.title != old_channel_info.title:
            notif_text = f"📜 @{payload.broadcaster.display_name} changed title: \"{payload.title}\""
            await self.push_notification(AlertType.TITLE, payload.broadcaster.id, notif_text)
        if payload.category_id != old_channel_info.game_id:
            notif_text = f"🎮 @{payload.broadcaster.display_name} changed game: \"{payload.category_name}\""
            await self.push_notification(AlertType.CATEGORY, payload.broadcaster.id, notif_text)
            
        old_channel_info.title = payload.title
        old_channel_info.language = payload.language
        old_channel_info.game_id = payload.category_id
        old_channel_info.game_name = payload.category_name
        old_channel_info.classification_labels = payload.content_classification_labels
        
    @commands.Component.listener()
    async def event_stream_online(self, payload: twitchio.StreamOnline):
        notif_text = f"🚀 @{payload.broadcaster.display_name} went live!"
        await self.push_notification(AlertType.LIVE, payload.broadcaster.id, notif_text)
        
    @commands.Component.listener()
    async def event_stream_offline(self, payload: twitchio.StreamOffline):
        notif_text = f"👋 @{payload.broadcaster.display_name} went offline!"
        await self.push_notification(AlertType.OFFLINE, payload.broadcaster.id, notif_text)