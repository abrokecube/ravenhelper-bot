import asyncio
import json
import asyncio
import websockets
import random
import string
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, NamedTuple, TypedDict, Iterable
import os
from dotenv import load_dotenv
import logging
load_dotenv()

TWITCH_PUBSUB = "wss://hermes.twitch.tv/v1?clientId=kimne78kx3ncx6brgo4mv6wki5h1ko"

class SubTopic(Enum):
    ADS = "ads"
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
    POLLS = "polls"
    PREDICTIONS = "predictions-user-v1"
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

def generate_id(length=21):
    chars = string.ascii_letters + string.digits + "_-"
    return ''.join(random.choices(chars, k=length))

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

class TwitchUserPubSub:
    def __init__(self, token: str):
        self.uri = TWITCH_PUBSUB
        self.websocket = None
        self.pending: Dict[id, asyncio.Future] = {}
        self.subscriptions: Dict[id, callable] = {}
        self.token = token

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)
        asyncio.create_task(self._listen())  # Start listening in background
        logging.info(f"Connected to {self.uri}")
        await self.authenticate()

    async def authenticate(self):
        r = await self.request("authenticate", {
            "token": self.token
        })
        if r['authenticateResponse']['result'] == "ok":
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
            pass
        elif result_code == "error":
            err_code = response['errorCode']
            if err_code == "SUB004":  # duplicate subscription
                subscription_id = response["SUB004"]["existingSubscriptionId"]
                logging.warning(f"Subscription {topic_code} already exists")
            else:
                raise Exception(f"Error while subscribing... Recieved: {r}")
        else:
            raise Exception(f"Error while subscribing (unknown response)... Recieved: {r}")
        self.subscriptions[subscription_id] = Subscription(subscription_id, channel_id, topic)

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
            logging.debug(f"Sent: {message}")
        else:
            raise RuntimeError("WebSocket is not connected.")        

    async def _listen(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                match data['type']:
                    case "welcome":
                        self.uri = data['welcome']['recoveryUrl']
                    case "notification":
                        asyncio.create_task(self.handle_notification(data))
                
                response_id = data.get("parentId")
                if response_id and response_id in self.pending:
                    # Complete the waiting future
                    self.pending[response_id].set_result(data)
                    del self.pending[response_id]
                    logging.debug(f"Received (+): {message}")
                else:
                    logging.debug(f"Received: {message}")
        except websockets.ConnectionClosed:
            logging.info("Connection closed")
            # Optionally cancel all pending futures
            for future in self.pending.values():
                future.cancel()

    async def close(self):
        if self.websocket:
            await self.websocket.close()
            logging.info("WebSocket closed.")

    async def run(self, reconnect_delay=5):
        while True:
            try:
                await self.connect()

                while True:
                    await asyncio.sleep(3600)
            except Exception as e:
                logging.error(f"Connection error: {e}")
                await asyncio.sleep(reconnect_delay)

    async def handle_notification(self, data):
        subscription = self.subscriptions[data['notification']['subscription']['id']]
        pubsub = json.loads(data['notification']['pubsub'])
        match pubsub['type']:
            case "pin-message":
                await self.event_message_pinned(subscription, pubsub['data'])
    
    async def event_message_pinned(self, subscription: Subscription, payload: PinnedMessage):
        pass

async def main():
    token = os.getenv("USER_TOKEN")
    if not token:
        raise Exception('erm where\'s my token')
    client = TwitchUserPubSub(token)
    await client.run()

if __name__ == "__main__":
    asyncio.run(main())
