-- Removes the categorie/article_categorie feature: book-to-genre assignment
-- was never reachable from the actual product UI (BookCreate/BookUpdate never
-- accepted categorie_ids, so article_categorie stayed empty in practice), and
-- the only UI that appeared to set it (admin book edit page) silently no-oped.
-- Dropping both tables rather than leaving unused schema around.
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `article_categorie`;
DROP TABLE IF EXISTS `categorie`;
SET FOREIGN_KEY_CHECKS = 1;
