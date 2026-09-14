from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from infrastructure import models
from infrastructure.crud_base import CrudBase
from presentation.deps import AdminUser, DbSession
from presentation.schemas import ArticleCreate, ArticleRead, ArticleUpdate

router = APIRouter(prefix="/articles", tags=["articles"])

article_crud = CrudBase[models.Article](models.Article, "id_article")


@router.get("/", response_model=list[ArticleRead])
@router.get("", response_model=list[ArticleRead], include_in_schema=False)
def list_articles(db: DbSession):
    # One handler serves both "/articles" and "/articles/" -- see
    # book_router.list_books for why (avoids a FastAPI redirect_slashes
    # redirect leaking the backend's own absolute origin to the browser
    # through the frontend's /api/proxy rewrite).
    return article_crud.list(db)


@router.get("/{id_article}", response_model=ArticleRead)
def get_article(id_article: int, db: DbSession):
    obj = article_crud.get(db, id_article)
    if obj is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return obj


@router.post("/", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=ArticleRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_article(
    payload: ArticleCreate,
    db: DbSession,
    _admin: AdminUser,
):
    return article_crud.create(db, models.Article(**payload.model_dump()))


@router.put("/{id_article}", response_model=ArticleRead)
def update_article(
    id_article: int,
    payload: ArticleUpdate,
    db: DbSession,
    _admin: AdminUser,
):
    obj = article_crud.update(db, id_article, payload.model_dump(exclude_unset=True))
    if obj is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return obj


@router.delete("/{id_article}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    id_article: int,
    db: DbSession,
    _admin: AdminUser,
):
    if not article_crud.delete(db, id_article):
        raise HTTPException(status_code=404, detail="Article not found")
    return None
