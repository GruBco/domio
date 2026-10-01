from asyncio import AbstractEventLoop, Future
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict

from scgi_server.local.services.rw_service.subservices.plc_comm_service.plc_cache.cache_value_condition import CacheValueCondition


@dataclass(frozen=True)
class CacheValue:
    value: str
    description: str
    condition: CacheValueCondition


class SinglePlcCache:
    """
    Cache for single plc
    """

    @dataclass(frozen=True)
    class Item:
        value: str
        description: str
        expiry: datetime

    def __init__(self,
                 loop: AbstractEventLoop,
                 request_period: timedelta,
                 valid_period: timedelta):
        self._loop: AbstractEventLoop = loop
        self._request_period: timedelta = request_period
        self._valid_period: timedelta = valid_period

        self._name_to_item_dict: Dict[str, 'Item'] = {}
        self._name_to_future_item_dict: Dict[str, Future] = {}

    def get_value(self, name: str) -> CacheValue:
        item = self._name_to_item_dict[name]
        return self._item_to_value(item)

    async def get_future_value(self, name: str) -> CacheValue:
        item = await self._name_to_future_item_dict[name]
        return self._item_to_value(item)

    def set_value(self, name: str, value: str, description: str) -> None:
        expiry = datetime.now() + self._valid_period
        item = self.Item(value, description, expiry)
        self._name_to_item_dict[name] = item

        try:
            future = self._name_to_future_item_dict[name]
            if not future.done():
                future.set_result(item)
            del self._name_to_future_item_dict[name]
        except KeyError:
            pass

    def start_future(self, name: str) -> None:
        self.cancel_future(name)
        self._name_to_future_item_dict[name] = self._loop.create_future()

    def cancel_future(self, name: str) -> None:
        try:
            self._name_to_future_item_dict[name].cancel()
            del self._name_to_future_item_dict[name]
        except KeyError:
            pass

    def cleanup(self) -> None:
        keys = list(self._name_to_item_dict.keys())
        for name in keys:
            value = self.get_value(name)
            if value.condition == CacheValueCondition.STALE:
                del self._name_to_item_dict[name]

    def _item_to_value(self, item: Item) -> CacheValue:
        condition = self._expiry_to_condition(item.expiry)
        return CacheValue(item.value, item.description, condition)

    def _expiry_to_condition(self, expiry: datetime) -> CacheValueCondition:
        stinky_time = expiry - self._request_period

        now = datetime.now()

        if now < stinky_time:
            return CacheValueCondition.FRESH
        elif now < expiry:
            return CacheValueCondition.STINKY
        else:
            return CacheValueCondition.STALE
