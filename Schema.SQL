CREATE DATABASE caribooks;

USE caribooks;

CREATE TABLE type_objet (
    id_type_objet BIGINT AUTO_INCREMENT PRIMARY KEY,
    libelle VARCHAR(100) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE etat_usure (
    id_etat_usure BIGINT AUTO_INCREMENT PRIMARY KEY,
    libelle VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE categorie (
    id_categorie BIGINT AUTO_INCREMENT PRIMARY KEY,
    libelle VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE article (
    id_article BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_type_objet BIGINT NOT NULL,
    id_etat_usure BIGINT NOT NULL,
    sku VARCHAR(100) NOT NULL UNIQUE,
    titre VARCHAR(255) NOT NULL,
    description TEXT,
    prix_chf DECIMAL(10,2) NOT NULL CHECK (prix_chf >= 0),
    actif BOOLEAN NOT NULL DEFAULT TRUE,
    date_creation TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_type_objet) REFERENCES type_objet(id_type_objet) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (id_etat_usure) REFERENCES etat_usure(id_etat_usure) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE livre (
    id_article BIGINT PRIMARY KEY,
    isbn VARCHAR(20) NOT NULL UNIQUE,
    auteur VARCHAR(255),
    editeur VARCHAR(255),
    date_publication DATE,
    langue VARCHAR(50),
    FOREIGN KEY (id_article) REFERENCES article(id_article) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE article_categorie (
    id_article BIGINT NOT NULL,
    id_categorie BIGINT NOT NULL,
    PRIMARY KEY (id_article, id_categorie),
    FOREIGN KEY (id_article) REFERENCES article(id_article) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_categorie) REFERENCES categorie(id_categorie) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE source_stock (
    id_source_stock BIGINT AUTO_INCREMENT PRIMARY KEY,
    libelle VARCHAR(150) NOT NULL,
    type_source VARCHAR(50) NOT NULL,
    description TEXT
);

CREATE TABLE stock (
    id_stock BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_article BIGINT NOT NULL,
    id_source_stock BIGINT NOT NULL,
    quantite_disponible INT NOT NULL DEFAULT 0 CHECK (quantite_disponible >= 0),
    quantite_reservee INT NOT NULL DEFAULT 0 CHECK (quantite_reservee >= 0),
    date_mise_a_jour TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_stock_article_source UNIQUE (id_article, id_source_stock),
    FOREIGN KEY (id_article) REFERENCES article(id_article) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_source_stock) REFERENCES source_stock(id_source_stock) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE utilisateur (
    id_utilisateur BIGINT AUTO_INCREMENT PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    mot_de_passe_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    date_creation TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ,billing_address_line1 VARCHAR(255) NULL
    ,billing_address_line2 VARCHAR(255) NULL
    ,billing_postal_code VARCHAR(30) NULL
    ,billing_city VARCHAR(100) NULL
    ,billing_country VARCHAR(100) NULL
    ,billing_phone VARCHAR(50) NULL
);

CREATE TABLE commande (
    id_commande BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_utilisateur BIGINT NOT NULL,
    numero_commande VARCHAR(50) NOT NULL UNIQUE,
    date_commande TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    montant_total_chf DECIMAL(10,2) NOT NULL CHECK (montant_total_chf >= 0),
    statut VARCHAR(50) NOT NULL,
    shipping_method VARCHAR(50) NOT NULL DEFAULT 'POST',
    frais_port_chf DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    FOREIGN KEY (id_utilisateur) REFERENCES utilisateur(id_utilisateur) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE ligne_commande (
    id_ligne_commande BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_commande BIGINT NOT NULL,
    id_article BIGINT NOT NULL,
    quantite INT NOT NULL CHECK (quantite > 0),
    prix_unitaire_chf DECIMAL(10,2) NOT NULL CHECK (prix_unitaire_chf >= 0),
    FOREIGN KEY (id_commande) REFERENCES commande(id_commande) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_article) REFERENCES article(id_article) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE paiement (
    id_paiement BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_commande BIGINT NOT NULL,
    fournisseur_paiement VARCHAR(50) NOT NULL DEFAULT 'POSTFINANCE',
    reference_externe VARCHAR(255) NOT NULL UNIQUE,
    montant_chf DECIMAL(10,2) NOT NULL CHECK (montant_chf >= 0),
    devise CHAR(3) NOT NULL DEFAULT 'CHF',
    statut VARCHAR(50) NOT NULL,
    date_paiement TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (id_commande) REFERENCES commande(id_commande) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE scan_isbn (
    id_scan_isbn BIGINT AUTO_INCREMENT PRIMARY KEY,
    id_utilisateur BIGINT NOT NULL,
    id_article_livre BIGINT NOT NULL,
    isbn_lu VARCHAR(20) NOT NULL,
    date_scan TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valide BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (id_utilisateur) REFERENCES utilisateur(id_utilisateur) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (id_article_livre) REFERENCES livre(id_article) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX idx_article_type_objet ON article(id_type_objet);
CREATE INDEX idx_article_etat_usure ON article(id_etat_usure);
CREATE INDEX idx_stock_article ON stock(id_article);
CREATE INDEX idx_stock_source ON stock(id_source_stock);
CREATE INDEX idx_commande_utilisateur ON commande(id_utilisateur);
CREATE INDEX idx_ligne_commande_commande ON ligne_commande(id_commande);
CREATE INDEX idx_ligne_commande_article ON ligne_commande(id_article);
CREATE INDEX idx_paiement_commande ON paiement(id_commande);
CREATE INDEX idx_scan_utilisateur ON scan_isbn(id_utilisateur);
CREATE INDEX idx_scan_livre ON scan_isbn(id_article_livre);
CREATE INDEX idx_livre_isbn ON livre(isbn);