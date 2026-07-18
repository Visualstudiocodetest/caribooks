from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from  infrastructure import models
from  infrastructure.crud_base import CrudBase
from  presentation.deps import get_db, require_admin
from  presentation.schemas import ArticleCreate, ArticleRead, ArticleUpdate

router = APIRouter(prefix="/articles", tags=["articles"])

article_crud = CrudBase[models.Article](models.Article, "id_article")


def _to_article_read(obj: models.Article) -> ArticleRead:
    return ArticleRead(
        id_article=int(obj.id_article),
        id_type_objet=int(obj.id_type_objet),
        id_etat_usure=int(obj.id_etat_usure),
        sku=obj.sku,
        titre=obj.titre,
        description=obj.description,
        image_link=obj.image_link,
        prix_chf=float(obj.prix_chf),
        actif=bool(obj.actif),
        date_creation=obj.date_creation,
        categorie_ids=[int(c.id_categorie) for c in (obj.categories or [])],
    )


@router.get("/", response_model=list[ArticleRead])
def list_articles(db: Session = Depends(get_db)):
    objs = db.query(models.Article).all()
    return [_to_article_read(o) for o in objs]


@router.get("/{id_article}", response_model=ArticleRead)
def get_article(id_article: int, db: Session = Depends(get_db)):
    obj = db.query(models.Article).filter(models.Article.id_article == id_article).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return _to_article_read(obj)


@router.post("/", response_model=ArticleRead, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: ArticleCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    obj = models.Article(
        id_type_objet=payload.id_type_objet,
        id_etat_usure=payload.id_etat_usure,
        sku=payload.sku,
        titre=payload.titre,
        description=payload.description,
        image_link=payload.image_link,
        prix_chf=payload.prix_chf,
        actif=payload.actif,
    )
    if payload.categorie_ids:
        cats = db.query(models.Categorie).filter(models.Categorie.id_categorie.in_(payload.categorie_ids)).all()
        obj.categories = cats
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_article_read(obj)


@router.put("/{id_article}", response_model=ArticleRead)
def update_article(
    id_article: int,
    payload: ArticleUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    obj = db.query(models.Article).filter(models.Article.id_article == id_article).first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Article not found")
    data = payload.model_dump(exclude_unset=True)
    categorie_ids = data.pop("categorie_ids", None)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    if categorie_ids is not None:
        cats = db.query(models.Categorie).filter(models.Categorie.id_categorie.in_(categorie_ids)).all()
        obj.categories = cats
    db.commit()
    db.refresh(obj)
    return _to_article_read(obj)


@router.delete("/{id_article}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    id_article: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    if not article_crud.delete(db, id_article):
        raise HTTPException(status_code=404, detail="Article not found")
    return None

