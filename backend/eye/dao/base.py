from typing import Protocol, TypeVar

Key = TypeVar("Key", contravariant=True)
Entity = TypeVar("Entity", covariant=True)


class BaseDAO(Protocol[Key, Entity]):
    def get_by_id(self, entity_id: Key) -> Entity | None:
        """按主键读取实体，找不到时返回 None。"""
        ...
