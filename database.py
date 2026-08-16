import os
import motor.motor_asyncio
import certifi
import json
from bson.objectid import ObjectId

MONGO_URI = os.getenv('MONGO_URI')
if not MONGO_URI:
    print("XATOLIK: MONGO_URI kiritilmagan! .env fayliga MONGO_URI kiriting.")
    exit(1)

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where(), tlsAllowInvalidCertificates=True)
db = client['sniper_bot_db']
users_coll = db['users']
signals_coll = db['signals']
kv_coll = db['kv_store']

async def init_db():
    pass

async def add_user(user_id: int):
    await users_coll.update_one(
        {'user_id': user_id}, 
        {
            '$set': {'user_id': user_id},
            '$setOnInsert': {'receive_signals': True, 'receive_macro': True}
        }, 
        upsert=True
    )

async def get_all_users() -> list:
    cursor = users_coll.find({})
    users = []
    async for doc in cursor:
        users.append(doc['user_id'])
    return users

async def get_users_for_signals() -> list:
    cursor = users_coll.find({"receive_signals": {"$ne": False}})
    users = []
    async for doc in cursor:
        users.append(doc['user_id'])
    return users

async def get_users_for_macro() -> list:
    cursor = users_coll.find({"receive_macro": {"$ne": False}})
    users = []
    async for doc in cursor:
        users.append(doc['user_id'])
    return users

async def get_user_settings(user_id: int) -> dict:
    doc = await users_coll.find_one({'user_id': user_id})
    if not doc:
        return {'receive_signals': True, 'receive_macro': True}
    return {
        'receive_signals': doc.get('receive_signals', True),
        'receive_macro': doc.get('receive_macro', True)
    }

async def update_user_setting(user_id: int, setting: str, value: bool):
    await users_coll.update_one({'user_id': user_id}, {'$set': {setting: value}})

async def add_signal(symbol, sig_type, entry, tp, tp2, sl, status, timestamp, message_ids, stars=5):
    msg_str = json.dumps(message_ids) if isinstance(message_ids, dict) else message_ids
    doc = {
        "symbol": symbol,
        "type": sig_type,
        "entry": entry,
        "tp": tp,
        "tp2": tp2,
        "sl": sl,
        "status": status,
        "timestamp": timestamp,
        "message_ids": msg_str,
        "stars": stars
    }
    await signals_coll.insert_one(doc)

async def get_pending_signals() -> list:
    cursor = signals_coll.find({"status": {"$in": ["PENDING", "TP1_HIT"]}})
    results = []
    async for doc in cursor:
        doc['id'] = str(doc['_id'])
        results.append(doc)
    return results

async def update_signal_status(signal_id, status, profit_pct=None):
    update_fields = {"status": status}
    if profit_pct is not None:
        update_fields["profit_pct"] = profit_pct
    await signals_coll.update_one({"_id": ObjectId(signal_id)}, {"$set": update_fields})

async def update_signal_sl(signal_id, sl):
    await signals_coll.update_one({"_id": ObjectId(signal_id)}, {"$set": {"sl": sl}})

async def get_weekly_signals_stats(start_time_iso: str):
    pipeline = [
        {"$match": {"timestamp": {"$gt": start_time_iso}, "status": {"$in": ['WIN', 'LOSS', 'BREAK_EVEN']}}},
        {"$group": {"_id": {"stars": "$stars", "status": "$status"}, "count": {"$sum": 1}, "total_profit": {"$sum": "$profit_pct"}}}
    ]
    cursor = signals_coll.aggregate(pipeline)
    results = []
    async for doc in cursor:
        results.append((doc['_id'].get('stars', 5), doc['_id'].get('status'), doc['count'], doc.get('total_profit', 0.0)))
    return results

async def get_daily_coin_stats(start_time_iso: str):
    pipeline = [
        {"$match": {"timestamp": {"$gt": start_time_iso}, "status": {"$in": ['WIN', 'LOSS', 'BREAK_EVEN']}}},
        {"$group": {"_id": {"stars": "$stars", "symbol": "$symbol", "status": "$status"}, "count": {"$sum": 1}, "total_profit": {"$sum": "$profit_pct"}}}
    ]
    cursor = signals_coll.aggregate(pipeline)
    results = []
    async for doc in cursor:
        results.append((doc['_id'].get('stars', 5), doc['_id'].get('symbol'), doc['_id'].get('status'), doc['count'], doc.get('total_profit', 0.0)))
    return results

async def get_last_news_link() -> str:
    doc = await kv_coll.find_one({"key": "last_news"})
    return doc['value'] if doc else ""

async def save_last_news_link(link: str):
    await kv_coll.update_one({"key": "last_news"}, {"$set": {"value": link}}, upsert=True)
