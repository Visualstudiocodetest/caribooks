-- Simplification: caribooks only ever sells books, so the generic
-- article/type_objet superclass (a table-per-class inheritance pattern meant
-- to leave room for future non-book object types) added indirection with no
-- payoff. This migration:
--   1. Moves article's columns (sku, titre, description, image_link,
--      prix_chf, actif, date_creation, id_etat_usure) directly onto livre.
--   2. Turns livre.id_article -- previously a shared-PK FK onto article --
--      into livre's own AUTO_INCREMENT primary key, renamed id_livre.
--   3. Re-points stock, ligne_commande and scan_isbn straight at
--      livre.id_livre (previously via article.id_article), renaming their FK
--      columns to id_livre (scan_isbn.id_article_livre -> id_livre too).
--   4. Drops the now-empty `article` and `type_objet` tables.
--
-- etat_usure is untouched: its FK simply moves from article to livre.

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Add article's columns onto livre and backfill from article.
ALTER TABLE `livre`
  ADD COLUMN `sku` varchar(100) NULL AFTER `id_article`,
  ADD COLUMN `titre` varchar(255) NULL AFTER `sku`,
  ADD COLUMN `description` text NULL AFTER `titre`,
  ADD COLUMN `image_link` varchar(500) NULL AFTER `description`,
  ADD COLUMN `prix_chf` decimal(10,2) NULL AFTER `image_link`,
  ADD COLUMN `actif` tinyint(1) NULL AFTER `prix_chf`,
  ADD COLUMN `date_creation` timestamp NULL AFTER `actif`,
  ADD COLUMN `id_etat_usure` bigint NULL AFTER `date_creation`;

UPDATE `livre` l
JOIN `article` a ON l.id_article = a.id_article
SET l.sku = a.sku,
    l.titre = a.titre,
    l.description = a.description,
    l.image_link = a.image_link,
    l.prix_chf = a.prix_chf,
    l.actif = a.actif,
    l.date_creation = a.date_creation,
    l.id_etat_usure = a.id_etat_usure;

-- 2. Re-apply article's original NOT NULL / default contract on livre.
ALTER TABLE `livre`
  MODIFY COLUMN `sku` varchar(100) NOT NULL,
  MODIFY COLUMN `titre` varchar(255) NOT NULL,
  MODIFY COLUMN `prix_chf` decimal(10,2) NOT NULL,
  MODIFY COLUMN `actif` tinyint(1) NOT NULL DEFAULT '1',
  MODIFY COLUMN `date_creation` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  MODIFY COLUMN `id_etat_usure` bigint NOT NULL,
  ADD CONSTRAINT `uq_livre_sku` UNIQUE (`sku`),
  ADD CONSTRAINT `livre_chk_1` CHECK ((`prix_chf` >= 0));

-- 3. Drop the FKs that point at article (or, for scan_isbn, at the old
-- shared-PK livre.id_article) so the columns beneath them can be renamed.
ALTER TABLE `livre` DROP FOREIGN KEY `livre_ibfk_1`;
ALTER TABLE `stock` DROP FOREIGN KEY `stock_ibfk_1`;
ALTER TABLE `ligne_commande` DROP FOREIGN KEY `ligne_commande_ibfk_2`;
ALTER TABLE `scan_isbn` DROP FOREIGN KEY `scan_isbn_ibfk_2`;

-- 4. Rename id_article -> id_livre everywhere; livre's becomes its own
-- AUTO_INCREMENT primary key instead of an FK-backed shared PK.
ALTER TABLE `livre` CHANGE COLUMN `id_article` `id_livre` bigint NOT NULL AUTO_INCREMENT;
ALTER TABLE `stock` CHANGE COLUMN `id_article` `id_livre` bigint NOT NULL;
ALTER TABLE `ligne_commande` CHANGE COLUMN `id_article` `id_livre` bigint NOT NULL;
ALTER TABLE `scan_isbn` CHANGE COLUMN `id_article_livre` `id_livre` bigint NOT NULL;

-- 5. Re-add the FKs against the renamed columns, pointing at livre.id_livre.
ALTER TABLE `livre`
  ADD KEY `idx_livre_etat_usure` (`id_etat_usure`),
  ADD CONSTRAINT `livre_ibfk_1` FOREIGN KEY (`id_etat_usure`) REFERENCES `etat_usure` (`id_etat_usure`) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE `stock`
  ADD CONSTRAINT `stock_ibfk_1` FOREIGN KEY (`id_livre`) REFERENCES `livre` (`id_livre`) ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE `ligne_commande`
  ADD CONSTRAINT `ligne_commande_ibfk_2` FOREIGN KEY (`id_livre`) REFERENCES `livre` (`id_livre`) ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE `scan_isbn`
  ADD CONSTRAINT `scan_isbn_ibfk_2` FOREIGN KEY (`id_livre`) REFERENCES `livre` (`id_livre`) ON DELETE CASCADE ON UPDATE CASCADE;

-- 6. Cosmetic: rename the old article-era index names to match.
ALTER TABLE `stock` RENAME INDEX `uq_stock_article_source` TO `uq_stock_livre_source`;
ALTER TABLE `stock` RENAME INDEX `idx_stock_article` TO `idx_stock_livre`;
ALTER TABLE `ligne_commande` RENAME INDEX `idx_ligne_commande_article` TO `idx_ligne_commande_livre`;

-- 7. Drop the now-empty article table and the type_objet lookup table.
DROP TABLE `article`;
DROP TABLE `type_objet`;

SET FOREIGN_KEY_CHECKS = 1;
