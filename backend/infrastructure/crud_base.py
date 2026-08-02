from __future__ import annotations

from typing import Any, Generic, Optional, Type, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class CrudBase(Generic[ModelT]):
    def __init__(self, model: Type[ModelT], pk_attr: str):
        self.model = model
        self.pk_attr = pk_attr

    def list(self, db: Session) -> list[ModelT]:
        return db.query(self.model).all()

    def get(self, db: Session, pk: Any) -> Optional[ModelT]:
        return db.query(self.model).filter(getattr(self.model, self.pk_attr) == pk).first()

    def create(self, db: Session, obj: ModelT) -> ModelT:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, pk: Any, data: dict[str, Any]) -> Optional[ModelT]:
        obj = self.get(db, pk)
        if obj is None:
            return None
        for k, v in data.items():
            if hasattr(obj, k):
                setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, pk: Any) -> bool:
        obj = self.get(db, pk)
        if obj is None:
            return False
        db.delete(obj)
        db.commit()
        return True

