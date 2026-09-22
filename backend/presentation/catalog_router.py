from __future__ import annotations

from fastapi import APIRouter

from infrastructure import models
from infrastructure.crud_base import CrudBase
from presentation.crud_router import simple_crud_router
from presentation.schemas import (
    EtatUsureCreate,
    EtatUsureRead,
    EtatUsureUpdate,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])

etat_usure_crud = CrudBase[models.EtatUsure](models.EtatUsure, "id_etat_usure")

router.include_router(
    simple_crud_router(
        prefix="",
        tags=["catalog"],
        path="etat-usures",
        crud=etat_usure_crud,
        read_schema=EtatUsureRead,
        create_schema=EtatUsureCreate,
        update_schema=EtatUsureUpdate,
        not_found="EtatUsure not found",
    )
)
