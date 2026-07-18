CREATE DATABASE IF NOT EXISTS `caribooks` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */;
USE `caribooks`;
SET FOREIGN_KEY_CHECKS = 0;

--
-- Table structure for table `type_objet`
--

CREATE TABLE IF NOT EXISTS `type_objet` (
  `id_type_objet` bigint NOT NULL AUTO_INCREMENT,
  `libelle` varchar(100) NOT NULL,
  `code` varchar(50) NOT NULL,
  `description` text,
  PRIMARY KEY (`id_type_objet`),
  UNIQUE KEY `code` (`code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `etat_usure`
--

CREATE TABLE IF NOT EXISTS `etat_usure` (
  `id_etat_usure` bigint NOT NULL AUTO_INCREMENT,
  `libelle` varchar(100) NOT NULL,
  `description` text,
  PRIMARY KEY (`id_etat_usure`),
  UNIQUE KEY `libelle` (`libelle`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `categorie`
--

CREATE TABLE IF NOT EXISTS `categorie` (
  `id_categorie` bigint NOT NULL AUTO_INCREMENT,
  `libelle` varchar(100) NOT NULL,
  `description` text,
  PRIMARY KEY (`id_categorie`),
  UNIQUE KEY `libelle` (`libelle`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `source_stock`
--

CREATE TABLE IF NOT EXISTS `source_stock` (
  `id_source_stock` bigint NOT NULL AUTO_INCREMENT,
  `libelle` varchar(150) NOT NULL,
  `type_source` varchar(50) NOT NULL,
  `description` text,
  PRIMARY KEY (`id_source_stock`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `utilisateur`
--

CREATE TABLE IF NOT EXISTS `utilisateur` (
  `id_utilisateur` bigint NOT NULL AUTO_INCREMENT,
  `nom` varchar(100) NOT NULL,
  `prenom` varchar(100) NOT NULL,
  `email` varchar(255) NOT NULL,
  `mot_de_passe_hash` varchar(255) DEFAULT NULL,
  `google_id` varchar(255) DEFAULT NULL,
  `role` varchar(50) NOT NULL DEFAULT 'user',
  `date_creation` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `billing_address_line1` varchar(255) DEFAULT NULL,
  `billing_address_line2` varchar(255) DEFAULT NULL,
  `billing_postal_code` varchar(30) DEFAULT NULL,
  `billing_city` varchar(100) DEFAULT NULL,
  `billing_country` varchar(100) DEFAULT NULL,
  `billing_phone` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id_utilisateur`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `google_id` (`google_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `article`
--

CREATE TABLE IF NOT EXISTS `article` (
  `id_article` bigint NOT NULL AUTO_INCREMENT,
  `id_type_objet` bigint NOT NULL,
  `id_etat_usure` bigint NOT NULL,
  `sku` varchar(100) NOT NULL,
  `titre` varchar(255) NOT NULL,
  `description` text,
  `image_link` varchar(500) DEFAULT NULL,
  `prix_chf` decimal(10,2) NOT NULL,
  `actif` tinyint(1) NOT NULL DEFAULT '1',
  `date_creation` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_article`),
  UNIQUE KEY `sku` (`sku`),
  KEY `idx_article_type_objet` (`id_type_objet`),
  KEY `idx_article_etat_usure` (`id_etat_usure`),
  CONSTRAINT `article_ibfk_1` FOREIGN KEY (`id_type_objet`) REFERENCES `type_objet` (`id_type_objet`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `article_ibfk_2` FOREIGN KEY (`id_etat_usure`) REFERENCES `etat_usure` (`id_etat_usure`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `article_chk_1` CHECK ((`prix_chf` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `article_categorie`
--

CREATE TABLE IF NOT EXISTS `article_categorie` (
  `id_article` bigint NOT NULL,
  `id_categorie` bigint NOT NULL,
  PRIMARY KEY (`id_article`,`id_categorie`),
  KEY `id_categorie` (`id_categorie`),
  CONSTRAINT `article_categorie_ibfk_1` FOREIGN KEY (`id_article`) REFERENCES `article` (`id_article`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `article_categorie_ibfk_2` FOREIGN KEY (`id_categorie`) REFERENCES `categorie` (`id_categorie`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `livre`
--

CREATE TABLE IF NOT EXISTS `livre` (
  `id_article` bigint NOT NULL,
  `isbn` varchar(20) NOT NULL,
  `auteur` varchar(255) DEFAULT NULL,
  `editeur` varchar(255) DEFAULT NULL,
  `date_publication` date DEFAULT NULL,
  `langue` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id_article`),
  UNIQUE KEY `isbn` (`isbn`),
  KEY `idx_livre_isbn` (`isbn`),
  CONSTRAINT `livre_ibfk_1` FOREIGN KEY (`id_article`) REFERENCES `article` (`id_article`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `stock`
--

CREATE TABLE IF NOT EXISTS `stock` (
  `id_stock` bigint NOT NULL AUTO_INCREMENT,
  `id_article` bigint NOT NULL,
  `id_source_stock` bigint NOT NULL,
  `quantite_disponible` int NOT NULL DEFAULT '0',
  `quantite_reservee` int NOT NULL DEFAULT '0',
  `date_mise_a_jour` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_stock`),
  UNIQUE KEY `uq_stock_article_source` (`id_article`,`id_source_stock`),
  KEY `idx_stock_article` (`id_article`),
  KEY `idx_stock_source` (`id_source_stock`),
  CONSTRAINT `stock_ibfk_1` FOREIGN KEY (`id_article`) REFERENCES `article` (`id_article`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `stock_ibfk_2` FOREIGN KEY (`id_source_stock`) REFERENCES `source_stock` (`id_source_stock`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `stock_chk_1` CHECK ((`quantite_disponible` >= 0)),
  CONSTRAINT `stock_chk_2` CHECK ((`quantite_reservee` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `commande`
--

CREATE TABLE IF NOT EXISTS `commande` (
  `id_commande` bigint NOT NULL AUTO_INCREMENT,
  `id_utilisateur` bigint NOT NULL,
  `numero_commande` varchar(50) NOT NULL,
  `date_commande` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `montant_total_chf` decimal(10,2) NOT NULL,
  `statut` varchar(50) NOT NULL,
  `shipping_method` varchar(50) NOT NULL DEFAULT 'POST',
  `frais_port_chf` decimal(10,2) NOT NULL DEFAULT '0.00',
  `cart_expires_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id_commande`),
  UNIQUE KEY `numero_commande` (`numero_commande`),
  KEY `idx_commande_utilisateur` (`id_utilisateur`),
  CONSTRAINT `commande_ibfk_1` FOREIGN KEY (`id_utilisateur`) REFERENCES `utilisateur` (`id_utilisateur`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `commande_chk_1` CHECK ((`montant_total_chf` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `ligne_commande`
--

CREATE TABLE IF NOT EXISTS `ligne_commande` (
  `id_ligne_commande` bigint NOT NULL AUTO_INCREMENT,
  `id_commande` bigint NOT NULL,
  `id_article` bigint NOT NULL,
  `quantite` int NOT NULL,
  `prix_unitaire_chf` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id_ligne_commande`),
  KEY `idx_ligne_commande_commande` (`id_commande`),
  KEY `idx_ligne_commande_article` (`id_article`),
  CONSTRAINT `ligne_commande_ibfk_1` FOREIGN KEY (`id_commande`) REFERENCES `commande` (`id_commande`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `ligne_commande_ibfk_2` FOREIGN KEY (`id_article`) REFERENCES `article` (`id_article`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `ligne_commande_chk_1` CHECK ((`quantite` > 0)),
  CONSTRAINT `ligne_commande_chk_2` CHECK ((`prix_unitaire_chf` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `paiement`
--

CREATE TABLE IF NOT EXISTS `paiement` (
  `id_paiement` bigint NOT NULL AUTO_INCREMENT,
  `id_commande` bigint NOT NULL,
  `fournisseur_paiement` varchar(50) NOT NULL DEFAULT 'POSTFINANCE',
  `reference_externe` varchar(255) NOT NULL,
  `montant_chf` decimal(10,2) NOT NULL,
  `devise` char(3) NOT NULL DEFAULT 'CHF',
  `statut` varchar(50) NOT NULL,
  `date_paiement` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id_paiement`),
  UNIQUE KEY `reference_externe` (`reference_externe`),
  KEY `idx_paiement_commande` (`id_commande`),
  CONSTRAINT `paiement_ibfk_1` FOREIGN KEY (`id_commande`) REFERENCES `commande` (`id_commande`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `paiement_chk_1` CHECK ((`montant_chf` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Table structure for table `scan_isbn`
--

CREATE TABLE IF NOT EXISTS `scan_isbn` (
  `id_scan_isbn` bigint NOT NULL AUTO_INCREMENT,
  `id_utilisateur` bigint NOT NULL,
  `id_article_livre` bigint NOT NULL,
  `isbn_lu` varchar(20) NOT NULL,
  `date_scan` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `valide` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id_scan_isbn`),
  KEY `idx_scan_utilisateur` (`id_utilisateur`),
  KEY `idx_scan_livre` (`id_article_livre`),
  CONSTRAINT `scan_isbn_ibfk_1` FOREIGN KEY (`id_utilisateur`) REFERENCES `utilisateur` (`id_utilisateur`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `scan_isbn_ibfk_2` FOREIGN KEY (`id_article_livre`) REFERENCES `livre` (`id_article`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

COMMIT;
