SET @dbname = DATABASE();
SET @tablename = 'utilisateur';
SET @columnname = 'google_id';
SET @preparedStatement = (SELECT IF(
  COUNT(*) = 0,
  'ALTER TABLE utilisateur ADD COLUMN google_id VARCHAR(255) NULL UNIQUE',
  'SELECT 1'
) FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = @dbname AND TABLE_NAME = @tablename AND COLUMN_NAME = @columnname);
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;
