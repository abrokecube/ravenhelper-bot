import asyncio
import json
import websockets
import random
import string
from datetime import datetime, timezone
from enum import Enum
from typing import NamedTuple, TypedDict, Literal, Any
from collections.abc import Iterable
import os
from dotenv import load_dotenv
import logging
import time
_ = load_dotenv()

TWITCH_PUBSUB = "wss://hermes.twitch.tv/v1?clientId=kimne78kx3ncx6brgo4mv6wki5h1ko"
LOGGER = logging.getLogger("hermes")

class SubTopic(Enum):
    ADS = "ads" # midroll_request
    AD_REFRESH = "ad-property-refresh"
    BIT_EVENTS = "channel-bit-events-public"
    BIT_REWARDS_CELEBRATIONS = "bits-rewards-celebration-v1"
    BROADCAST_SETTINGS_UPDATE = "broadcast-settings-update"
    CELEBRATIONS = "celebration-events-v1"
    CHARITY_CAMPAIGN_DONATIONS = "charity-campaign-donation-events-v1"
    COMMUNITY_POINTS = "community-points-channel-v1"
    CONTENT_CLASSIFICATION_LABELS = "content-classification-labels-v1"
    CREATOR_GOALS = "creator-goals-events-v1"
    GUEST_STAR = "guest-star-channel-v1"
    HYPE_TRAIN = "hype-train-events-v2"
    PINS = "pinned-chat-updates-v1"
    PREDICTIONS = "predictions-channel-v1"
    POLLS = "polls"
    RAIDS = "raid"
    SHOUTOUTS = "shoutout"
    SHARED_CHAT = "shared-chat-channel-v1"
    SPONSORSHIPS = "sponsorships-v1"
    STREAM_CHAT_ROOM = "stream-chat-room-v1"
    SUB_GIFTS = "channel-sub-gifts-v1"

class Subscription(NamedTuple):
    subscription_id: str
    channel_id: str
    topic: SubTopic

def generate_timestamp():
    now = datetime.now(timezone.utc)
    return now.isoformat(timespec='milliseconds').replace('+00:00', 'Z')

def generate_id(length: int=21) -> str:
    chars = string.ascii_letters + string.digits + "_-"
    return ''.join(random.choices(chars, k=length))

class UnknownResponse(Exception):
    def __init__(self, *args: Any):
        super().__init__(*args)

class SubscriptionError(Exception):
    def __init__(self, *args: Any):
        super().__init__(*args)

class PartialUser(TypedDict):
    id: str
    display_name: str

class UserBadge(TypedDict):
    id: str
    version: str

class Author(TypedDict):
    id: str
    display_name: str
    badges: Iterable[UserBadge]
    chat_color: str

class MessageFragment(TypedDict):
    text: str

class MessageContent(TypedDict):
    text: str
    fragments: Iterable[MessageFragment]

class Message(TypedDict):
    id: str
    sender: Author
    content: MessageContent
    type: str
    starts_at: int
    updated_at: int
    ends_at: int
    sent_at: int

class PinnedMessage(TypedDict):
    id: str
    pinned_by: PartialUser
    message: Message

class UnpinnedMessage(TypedDict):
    id: str
    unpinned_by: PartialUser
    reason: Literal["UNPIN"]
    
class PollSettings(TypedDict):
    multi_choice: ...
    bits_votes: ...
    channel_points_votes: ...

class PollVotes(TypedDict):
    total: int
    bits: int
    channel_points: int
    base: int

class PollTokens(TypedDict):
    bits: int
    channel_points: int

class PollChoice(TypedDict):
    choice_id: str
    title: str
    votes: PollVotes
    tokens: PollTokens
    total_voters: int

class Poll(TypedDict):
    poll_id: str
    owned_by: str
    created_by: str
    title: str
    started_at: str
    ended_at: str | None
    ended_by: str | None
    duration_seconds: int
    settings: PollSettings
    status: Literal["ACTIVE", "COMPLETED", "ARCHIVED"]
    choices: Iterable[PollChoice]
    votes: PollVotes
    tokens: PollTokens
    remaining_duration_milliseconds: int
    top_contributor: str | None
    top_bits_contributor: str | None
    top_channel_points_contributor: str | None

class Raid(TypedDict):
    id: str
    creator_id: str
    source_id: str
    target_id: str
    target_login: str
    target_display_name: str
    target_profile_image: str
    transition_jitter_seconds: int
    force_raid_now_seconds: int
    viewer_count: int

class PredictionUser(TypedDict):
    type: Literal['USER']
    user_id: str
    user_display_name: str
    extension_client_id: None | str

class PredictionResult(TypedDict):
    type: Literal["WIN", "LOSE", "REFUND"]
    points_won: int | None
    is_acknowledged: bool

class Predictor(TypedDict):
    id: str
    event_id: str
    outcome_id: str
    channel_id: str
    points: int
    predicted_at: str
    updated_at: str
    user_id: str
    result: None  # TODO: erm
    user_display_name: str    

class PredictionBadge(TypedDict):
    version: str
    set_id: str

class PredictionOutcome(TypedDict):
    id: str
    color: Literal["BLUE", "PINK"]
    title: str
    total_points: int
    total_users: int
    top_predictors: list[Predictor]
    badge: PredictionBadge

class Prediction(TypedDict):
    id: str
    channel_id: str
    created_at: str
    created_by: PredictionUser
    ended_at: str
    ended_by: PredictionUser | None
    locked_at: str
    locked_by: PredictionUser | None
    outcomes: list[PredictionOutcome]
    prediction_window_seconds: int
    status: Literal["ACTIVE", "LOCKED", "RESOLVE_PENDING", "RESOLVED", "CANCEL_PENDING", "CANCELED"]
    title: str
    winning_outcome_id: str | None

class ChannelUpdate(TypedDict):
    channel_id: str
    type: str
    channel: str
    old_status: str
    status: str
    old_game: str
    game: str
    old_game_id: int
    game_id: int

class TwitchUserPubSub:
    def __init__(self, token: str):
        self.uri = TWITCH_PUBSUB
        self.reconnect_uri = None
        self.websocket = None
        self.pending: dict[str, asyncio.Future] = {}
        self.subscriptions: dict[str, Subscription] = {}
        self.token = token
        self.last_connect_attempt = 0
        self.connect_retry_count = 0
        self.queue_resubscribe = False
        self.keepalive_s = 15
        self.reconnect_on_keepalive_fail_task: asyncio.Task = None
        self.authenticated = False
        
        self.raids: set[str] = set()
        self.predictions: dict[str, str] = {}

    async def event_started(self):
        pass
            
    async def _connect(self):
        uri = self.uri
        if self.reconnect_uri is not None:
            uri = self.reconnect_uri
            LOGGER.info(f"Using provided reconnect uri...")
        self.last_connect_attempt = time.time()
        retries = 0
        while True:
            try:
                self.websocket = await websockets.connect(uri)
                break
            except (OSError, websockets.InvalidHandshake, TimeoutError):
                retry_time = min(retries ** 2.5, 600)
                LOGGER.error(f"Websocket connection failed! Trying again in {retry_time}s")
                await asyncio.sleep(retry_time)
                retries += 1
                pass
        asyncio.create_task(self._listen())  # Start listening in background
        LOGGER.info(f"Connected to {uri}")
        if self.reconnect_uri is not None:
            self.reconnect_uri = None
        else:
            await self.authenticate()
        if self.queue_resubscribe:
            await self.resubscribe_all()
            self.queue_resubscribe = False

    async def authenticate(self):
        self.authenticated = False
        LOGGER.info("Attempting to authenticate")
        r = await self.request("authenticate", {
            "token": self.token
        })
        if r['authenticateResponse']['result'] == "ok":
            LOGGER.info("Successfully authenticated")
            self.authenticated = True
            return
        else:
            raise Exception("Failed to authenticate!")
    
    async def subscribe(self, topic: SubTopic, channel_id: str):
        subscription_id = generate_id()
        topic_code = f"{topic.value}.{channel_id}"
        r = await self.request("subscribe", {
            "id": subscription_id,
            "type": "pubsub",
            "pubsub": {
                "topic": topic_code
            }
        })
        response = r['subscribeResponse']
        result_code = response['result']
        if result_code == "ok":
            LOGGER.info(f"Subscribed to {topic_code}")
            pass
        elif result_code == "error":
            err_code = response['errorCode']
            if err_code == "SUB004":  # duplicate subscription
                subscription_id = response["SUB004"]["existingSubscriptionId"]
                LOGGER.warning(f"Subscription {topic_code} already exists")
            else:
                raise SubscriptionError(f"Error while subscribing... Recieved: {r}")
        else:
            raise UnknownResponse(f"Error while subscribing (unknown response)... Recieved: {r}")
        self.subscriptions[subscription_id] = Subscription(subscription_id, channel_id, topic)
    
    async def resubscribe_all(self):
        subscriptions = self.subscriptions.copy()
        self.subscriptions.clear()
        for subscription in subscriptions.values():
            asyncio.create_task(self.subscribe(subscription.topic, subscription.channel_id))

    async def request(self, type: str, payload):
        cid = generate_id()
        await self._send_ws(json.dumps(
            {
                "id": cid,
                "type": type,
                "timestamp": generate_timestamp(),
                type: payload
            }
        ))
        future = asyncio.get_event_loop().create_future()
        self.pending[cid] = future
        return await future

        
    async def _send_ws(self, message):
        if self.websocket:
            await self.websocket.send(message)
            LOGGER.debug(f"Sent: {message}")
        else:
            raise RuntimeError("WebSocket is not connected.")     
        
    async def keepalive_timeout(self):
        await asyncio.sleep(self.keepalive_s)
        LOGGER.info("Keepalive timed out")
        await self.websocket.close()

    async def _listen(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                if data['type'] != "keepalive":
                    print(data)
                self.reset_keepalive()
                match data['type']:
                    case "welcome":
                        self.reconnect_uri = data['welcome']['recoveryUrl']
                        # self.uri = data['welcome']['recoveryUrl']
                        self.keepalive_s = data['welcome']['keepaliveSec'] + 3
                    case "reconnect":
                        self.reconnect_uri = data['reconnect']['url']
                        LOGGER.info("Twitch sent reconnect message, closing connection...")
                        old_ws = self.websocket
                        LOGGER.info("Opening new connection")
                        await self._connect()
                        LOGGER.info("Closing old connection")
                        await old_ws.close()
                        LOGGER.info("Connection closed manually")
                        return
                    case "notification":
                        asyncio.create_task(self.handle_notification(data))
                    case "subscribeResponse":
                        pass
                    case "keepalive":
                        pass
                    case "authenticateResponse":
                        pass
                    case _:
                        print("--------- UNKNOWN MESSAGE: ")
                        print(data)
                
                response_id = data.get("parentId")
                if response_id and response_id in self.pending:
                    # Complete the waiting future
                    self.pending[response_id].set_result(data)
                    del self.pending[response_id]
                    LOGGER.debug(f"Received (+): {message}")
                else:
                    LOGGER.debug(f"Received: {message}")
        except websockets.ConnectionClosed as e:
            if e.code in (4123, 4122):  # "challenge expired" "invalid challenge"
                self.uri = TWITCH_PUBSUB
                self.queue_resubscribe = True
        time_since = time.time() - self.last_connect_attempt
        if time_since > 60:
            self.connect_retry_count = 0
        retry_time = min(self.connect_retry_count ** 2.5, 600)
        LOGGER.info(f"Connection closed, reconnecting in {retry_time}s")
        if not self.authenticated:
            self.uri = TWITCH_PUBSUB
            self.queue_resubscribe = True
            LOGGER.info(f"Authentication was never completed")
        await asyncio.sleep(retry_time)
        self.connect_retry_count += 1
        asyncio.create_task(self._connect())

    def reset_keepalive(self):
        if self.reconnect_on_keepalive_fail_task:
            self.reconnect_on_keepalive_fail_task.cancel()
        self.reconnect_on_keepalive_fail_task = asyncio.create_task(self.keepalive_timeout())
    
    async def close(self):
        if self.websocket:
            await self.websocket.close()
            LOGGER.info("WebSocket closed.")

    async def run(self, reconnect_delay=5):
        # while True:
            # try:
                await self._connect()
                await self.event_started()

                # while True:
                #     await asyncio.sleep(3600)
            # except Exception as e:
            #     LOGGER.error(f"Connection error: {e}")
            #     await asyncio.sleep(reconnect_delay)

    async def handle_notification(self, data):
        subscription = self.subscriptions[data['notification']['subscription']['id']]
        pubsub = json.loads(data['notification']['pubsub'])
        match pubsub['type'].lower():
            case "pin-message":
                await self.event_message_pinned(subscription, pubsub['data'])
            case "unpin-message":
                await self.event_message_unpinned(subscription, pubsub['data'])
            case "poll_create":
                await self.event_poll_started(subscription, pubsub['data']['poll'])
            case "poll_update":
                await self.event_poll_updated(subscription, pubsub['data']['poll'])
            case "poll_complete":
                await self.event_poll_completed(subscription, pubsub['data']['poll'])
            case "raid_update_v2":
                raid: Raid = pubsub['raid']
                await self.event_raid_updated(subscription, raid)
                if not raid["source_id"] in self.raids:
                    await self.event_raid_started(subscription, raid)
                    self.raids.add(raid['source_id'])
            case "raid_cancel_v2":
                raid: Raid = pubsub['raid']
                await self.event_raid_updated(subscription, pubsub['raid'])
                if raid["source_id"] in self.raids:
                    await self.event_raid_cancelled(subscription, raid)
                    self.raids.remove(raid['source_id'])
            case "raid_go_v2":
                raid: Raid = pubsub['raid']
                await self.event_raid_updated(subscription, pubsub['raid'])
                if raid["source_id"] in self.raids:
                    await self.event_raid_completed(subscription, raid)
                    self.raids.remove(raid['source_id'])
            case "event-created":
                prediction: Prediction = pubsub['data']['event']
                await self.event_prediction_started(subscription, prediction)
                self.predictions[prediction["id"]] = prediction["status"]
            case "event-updated":
                prediction: Prediction = pubsub['data']['event']
                if not prediction["id"] in self.predictions:
                    self.predictions[prediction["id"]] = None
                aga = False
                if self.predictions[prediction["id"]] != prediction['status']:
                    ended = False
                    match prediction['status']:
                        case "ACTIVE":
                            ...
                        case "LOCKED":
                            await self.event_prediction_locked(subscription, prediction)
                        case "RESOLVE_PENDING":
                            if prediction["outcomes"][0]["top_predictors"][0]["result"] is not None:
                                await self.event_prediction_resolved(subscription, prediction)
                            else:
                                aga = True
                        case "RESOLVED":
                            ended = True
                        case "CANCEL_PENDING":  
                            await self.event_prediction_cancelled(subscription, prediction)
                        case "CANCELED":
                            ended = True
                        case _:
                            prediction['title'] += f" ( @abrokecube unknown prediction status: {prediction['status']} )"
                            LOGGER.warning(f"UNKNOWN PREDICTION STATUS: {prediction['status']}")
                    if not ended:
                        if not aga:
                            self.predictions[prediction["id"]] = prediction['status']
                    else:
                        self.predictions.pop(prediction["id"])
                await self.event_prediction_updated(subscription, prediction)
            case "broadcast_settings_update":
                await self.event_channel_updated(subscription, pubsub)
            case _:
                print("--------- UNKNOWN NOTIFICATION: ")
                print(data)
    
    async def event_message_pinned(self, subscription: Subscription, payload: PinnedMessage):
        pass

    async def event_message_unpinned(self, subscription: Subscription, payload: UnpinnedMessage):
        pass

    async def event_poll_started(self, subscription: Subscription, payload: Poll):
        pass

    async def event_poll_updated(self, subscription: Subscription, payload: Poll):
        pass

    async def event_poll_completed(self, subscription: Subscription, payload: Poll):
        pass
    
    async def event_raid_started(self, subscription: Subscription, payload: Raid):
        pass

    async def event_raid_updated(self, subscription: Subscription, payload: Raid):
        pass

    async def event_raid_cancelled(self, subscription: Subscription, payload: Raid):
        pass

    async def event_raid_completed(self, subscription: Subscription, payload: Raid):
        pass
    
    async def event_prediction_started(self, subscription: Subscription, payload: Prediction):
        pass
        
    async def event_prediction_updated(self, subscription: Subscription, payload: Prediction):
        pass

    async def event_prediction_locked(self, subscription: Subscription, payload: Prediction):
        pass

    async def event_prediction_cancelled(self, subscription: Subscription, payload: Prediction):
        pass

    async def event_prediction_resolved(self, subscription: Subscription, payload: Prediction):
        pass
    
    async def event_channel_updated(self, subscription: Subscription, payload: ChannelUpdate):
        pass

async def main():
    token = os.getenv("USER_TOKEN")
    if not token:
        raise Exception('erm where\'s my token')
    client = TwitchUserPubSub(token)
    await client.run()

if __name__ == "__main__":
    asyncio.run(main())
