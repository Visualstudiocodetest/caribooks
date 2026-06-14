SET @dbname = DATABASE();
SET @tablename = 'commande';
SET @columnname = 'cart_expires_at';
SET @preparedStatement = (SELECT IF(
  COUNT(*) = 0,
  'ALTER TABLE commande ADD COLUMN cart_expires_at TIMESTAMP NULL DEFAULT NULL',
  'SELECT 1'
) FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = @tablename AND COLUMN_NAME = @columnname);
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;
