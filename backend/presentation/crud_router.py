from typing import Type, TypeVar

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from infrastructure.crud_base import CrudBase
from presentation.deps import AdminUser, DbSession

# NOT `from __future__ import annotations` in this module: the endpoint
# closures below parameterize their signature with `create_schema`/
# `update_schema`, which are local variables of simple_crud_router, not
# module globals. Postponed evaluation (PEP 563) would turn
# `payload: create_schema` into the *string* "create_schema", which FastAPI
# then can't resolve back to the actual Pydantic model (it only resolves
# string annotations against module globals / class namespaces, never an
# enclosing function's locals) -- it would silently fall back to treating
# `payload` as a query parameter instead of a request body.

ModelT = TypeVar("ModelT")


def simple_crud_router(
    *,
    prefix: str,
    tags: list[str],
    path: str,
    crud: CrudBase[ModelT],
    read_schema: Type[BaseModel],
    create_schema: Type[BaseModel],
    update_schema: Type[BaseModel],
    not_found: str,
) -> APIRouter:
    """Build the standard list/get/create/update/delete endpoints for a plain
    reference-data resource: no ownership, no business rules beyond
    admin-gated writes (e.g. TypeObjet, EtatUsure). catalog_router.py used to
    hand-write these twice, identical apart from the model/schema names.

    Anything with real logic beyond that (filters, ownership, side effects —
    e.g. stock_router.py, order_router.py) stays a hand-written router; this
    factory only replaces routers that were pure CrudBase boilerplate.

    The path parameter is always named `item_id` here regardless of the
    resource -- that's a Python-side implementation detail invisible in the
    actual URL (e.g. still `/catalog/type-objets/42`), so it doesn't change
    the public API at all.
    """
    router = APIRouter(prefix=prefix, tags=tags)

    @router.get(f"/{path}", response_model=list[read_schema])
    def list_items(db: DbSession):
        return crud.list(db)

    @router.get(f"/{path}/{{item_id}}", response_model=read_schema)
    def get_item(item_id: int, db: DbSession):
        obj = crud.get(db, item_id)
        if obj is None:
            raise HTTPException(status_code=404, detail=not_found)
        return obj

    @router.post(f"/{path}", response_model=read_schema, status_code=status.HTTP_201_CREATED)
    def create_item(payload: create_schema, db: DbSession, _admin: AdminUser):  # type: ignore[valid-type]
        return crud.create(db, crud.model(**payload.model_dump()))

    @router.put(f"/{path}/{{item_id}}", response_model=read_schema)
    def update_item(item_id: int, payload: update_schema, db: DbSession, _admin: AdminUser):  # type: ignore[valid-type]
        updated = crud.update(db, item_id, payload.model_dump(exclude_unset=True))
        if updated is None:
            raise HTTPException(status_code=404, detail=not_found)
        return updated

    @router.delete(f"/{path}/{{item_id}}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_item(item_id: int, db: DbSession, _admin: AdminUser):
        if not crud.delete(db, item_id):
            raise HTTPException(status_code=404, detail=not_found)
        return None

    return router
