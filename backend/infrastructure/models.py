from __future__ import annotations
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from infrastructure.db import Base
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    DECIMAL,
)



article_categorie = Table(
    "article_categorie",
    Base.metadata,
    Column(
        "id_article",
        BigInteger,
        ForeignKey("article.id_article", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    ),
    Column(
        "id_categorie",
        BigInteger,
        ForeignKey("categorie.id_categorie", ondelete="RESTRICT", onupdate="CASCADE"),
        primary_key=True,
    ),
)

class Article(Base):
    __tablename__ = "article"
    id_article = Column(BigInteger, primary_key=True, autoincrement=True)
    id_type_objet = Column(
        BigInteger, ForeignKey("type_objet.id_type_objet", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False
    )
    id_etat_usure = Column(
        BigInteger, ForeignKey("etat_usure.id_etat_usure", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False
    )
    sku = Column(String(100), unique=True, nullable=False)
    titre = Column(String(255), nullable=False)
    description = Column(Text)
    image_link = Column(String(500))
    prix_chf = Column(DECIMAL(10, 2), nullable=False)
    actif = Column(Boolean, default=True, nullable=False)
    date_creation = Column(TIMESTAMP, nullable=False, server_default=func.now())

    __table_args__ = (CheckConstraint("prix_chf >= 0", name="ck_article_prix_chf_nonneg"),)

    type_objet = relationship("TypeObjet")
    etat_usure = relationship("EtatUsure")
    livre = relationship("Livre", back_populates="article", uselist=False)
    categories = relationship("Categorie", secondary=article_categorie, back_populates="articles")
    stocks = relationship("Stock", back_populates="article")
    lignes_commande = relationship("LigneCommande", back_populates="article")

class Livre(Base):
    __tablename__ = "livre"
    id_article = Column(
        BigInteger,
        ForeignKey("article.id_article", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    isbn = Column(String(20), unique=True, nullable=False)
    auteur = Column(String(255))
    editeur = Column(String(255))
    date_publication = Column(Date)
    langue = Column(String(50))
    article = relationship("Article", back_populates="livre")
    scans = relationship("ScanISBN", back_populates="livre", cascade="all, delete-orphan", passive_deletes=True)


class TypeObjet(Base):
    __tablename__ = "type_objet"
    id_type_objet = Column(BigInteger, primary_key=True, autoincrement=True)
    libelle = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text)

    articles = relationship("Article", back_populates="type_objet")


class EtatUsure(Base):
    __tablename__ = "etat_usure"
    id_etat_usure = Column(BigInteger, primary_key=True, autoincrement=True)
    libelle = Column(String(100), nullable=False, unique=True)
    description = Column(Text)

    articles = relationship("Article", back_populates="etat_usure")


class Categorie(Base):
    __tablename__ = "categorie"
    id_categorie = Column(BigInteger, primary_key=True, autoincrement=True)
    libelle = Column(String(100), nullable=False, unique=True)
    description = Column(Text)

    articles = relationship("Article", secondary=article_categorie, back_populates="categories")


class SourceStock(Base):
    __tablename__ = "source_stock"
    id_source_stock = Column(BigInteger, primary_key=True, autoincrement=True)
    libelle = Column(String(150), nullable=False)
    type_source = Column(String(50), nullable=False)
    description = Column(Text)

    stocks = relationship("Stock", back_populates="source_stock")


class Stock(Base):
    __tablename__ = "stock"
    id_stock = Column(BigInteger, primary_key=True, autoincrement=True)
    id_article = Column(
        BigInteger, ForeignKey("article.id_article", ondelete="CASCADE", onupdate="CASCADE"), nullable=False
    )
    id_source_stock = Column(
        BigInteger,
        ForeignKey("source_stock.id_source_stock", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    quantite_disponible = Column(Integer, nullable=False, server_default="0")
    quantite_reservee = Column(Integer, nullable=False, server_default="0")
    date_mise_a_jour = Column(TIMESTAMP, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("id_article", "id_source_stock", name="uq_stock_article_source"),
        CheckConstraint("quantite_disponible >= 0", name="ck_stock_qte_dispo_nonneg"),
        CheckConstraint("quantite_reservee >= 0", name="ck_stock_qte_res_nonneg"),
    )

    article = relationship("Article", back_populates="stocks")
    source_stock = relationship("SourceStock", back_populates="stocks")

class Utilisateur(Base):
    __tablename__ = "utilisateur"
    id_utilisateur = Column(BigInteger, primary_key=True, autoincrement=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    mot_de_passe_hash = Column(String(255), nullable=True)
    google_id = Column(String(255), nullable=True, unique=True)
    role = Column(String(50), nullable=False, default="user")
    # Billing address fields
    billing_address_line1 = Column(String(255), nullable=True)
    billing_address_line2 = Column(String(255), nullable=True)
    billing_postal_code = Column(String(30), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_country = Column(String(100), nullable=True)
    billing_phone = Column(String(50), nullable=True)
    date_creation = Column(TIMESTAMP, nullable=False, server_default=func.now())

    commandes = relationship("Commande", back_populates="utilisateur")
    scans = relationship("ScanISBN", back_populates="utilisateur")


class Commande(Base):
    __tablename__ = "commande"
    id_commande = Column(BigInteger, primary_key=True, autoincrement=True)
    id_utilisateur = Column(
        BigInteger, ForeignKey("utilisateur.id_utilisateur", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False
    )
    numero_commande = Column(String(50), nullable=False, unique=True)
    date_commande = Column(TIMESTAMP, nullable=False, server_default=func.now())
    montant_total_chf = Column(DECIMAL(10, 2), nullable=False)
    # Shipping / pickup options
    shipping_method = Column(String(50), nullable=False, server_default="POST")
    frais_port_chf = Column(DECIMAL(10, 2), nullable=False, server_default="0.00")
    statut = Column(String(50), nullable=False)

    __table_args__ = (CheckConstraint("montant_total_chf >= 0", name="ck_commande_total_nonneg"),)

    utilisateur = relationship("Utilisateur", back_populates="commandes")
    lignes = relationship("LigneCommande", back_populates="commande", cascade="all, delete-orphan")
    paiements = relationship("Paiement", back_populates="commande")


class LigneCommande(Base):
    __tablename__ = "ligne_commande"
    id_ligne_commande = Column(BigInteger, primary_key=True, autoincrement=True)
    id_commande = Column(
        BigInteger, ForeignKey("commande.id_commande", ondelete="CASCADE", onupdate="CASCADE"), nullable=False
    )
    id_article = Column(
        BigInteger, ForeignKey("article.id_article", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False
    )
    quantite = Column(Integer, nullable=False)
    prix_unitaire_chf = Column(DECIMAL(10, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("quantite > 0", name="ck_ligne_commande_qte_pos"),
        CheckConstraint("prix_unitaire_chf >= 0", name="ck_ligne_commande_prix_nonneg"),
    )

    commande = relationship("Commande", back_populates="lignes")
    article = relationship("Article", back_populates="lignes_commande")


class Paiement(Base):
    __tablename__ = "paiement"
    id_paiement = Column(BigInteger, primary_key=True, autoincrement=True)
    id_commande = Column(
        BigInteger, ForeignKey("commande.id_commande", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False
    )
    fournisseur_paiement = Column(String(50), nullable=False, server_default="POSTFINANCE")
    reference_externe = Column(String(255), nullable=False, unique=True)
    montant_chf = Column(DECIMAL(10, 2), nullable=False)
    devise = Column(String(3), nullable=False, server_default="CHF")
    statut = Column(String(50), nullable=False)
    date_paiement = Column(TIMESTAMP, nullable=True)

    __table_args__ = (CheckConstraint("montant_chf >= 0", name="ck_paiement_montant_nonneg"),)

    commande = relationship("Commande", back_populates="paiements")


class ScanISBN(Base):
    __tablename__ = "scan_isbn"
    id_scan_isbn = Column(BigInteger, primary_key=True, autoincrement=True)
    id_utilisateur = Column(
        BigInteger, ForeignKey("utilisateur.id_utilisateur", ondelete="CASCADE", onupdate="CASCADE"), nullable=False
    )
    id_article_livre = Column(
        BigInteger, ForeignKey("livre.id_article", ondelete="CASCADE", onupdate="CASCADE"), nullable=False
    )
    isbn_lu = Column(String(20), nullable=False)
    date_scan = Column(TIMESTAMP, nullable=False, server_default=func.now())
    valide = Column(Boolean, nullable=False, server_default="0")

    utilisateur = relationship("Utilisateur", back_populates="scans")
    livre = relationship("Livre", back_populates="scans", passive_deletes=True)
