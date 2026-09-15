-- Tracks exactly which Stock row(s) a paid ligne_commande's quantity was taken
-- from, so a refund can credit quantite_disponible back on those same rows
-- instead of dumping the whole refund into one arbitrary row (a real bug:
-- totals stayed correct, but the per-source-stock breakdown drifted after
-- every refund). Written by finalize_commande, consumed and deleted by
-- refund_commande.
CREATE TABLE IF NOT EXISTS `stock_mouvement` (
  `id_mouvement` bigint NOT NULL AUTO_INCREMENT,
  `id_ligne_commande` bigint NOT NULL,
  `id_stock` bigint NOT NULL,
  `quantite` int NOT NULL,
  `date_mouvement` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id_mouvement`),
  KEY `idx_stock_mouvement_ligne` (`id_ligne_commande`),
  KEY `idx_stock_mouvement_stock` (`id_stock`),
  CONSTRAINT `stock_mouvement_ibfk_1` FOREIGN KEY (`id_ligne_commande`) REFERENCES `ligne_commande` (`id_ligne_commande`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `stock_mouvement_ibfk_2` FOREIGN KEY (`id_stock`) REFERENCES `stock` (`id_stock`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `stock_mouvement_chk_1` CHECK ((`quantite` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
