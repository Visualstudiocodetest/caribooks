-- Migration: Add image_link to article table
SET @dbname = DATABASE();
SET @tablename = 'article';
SET @columnname = 'image_link';
SET @preparedStatement = (
  SELECT IF(
    COUNT(*) = 0,
    'ALTER TABLE article ADD COLUMN image_link VARCHAR(500) NULL AFTER description',
    'SELECT 1'
  )
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = @dbname
    AND TABLE_NAME = @tablename
    AND COLUMN_NAME = @columnname
);
PREPARE alterIfNotExists FROM @preparedStatement;
EXECUTE alterIfNotExists;
DEALLOCATE PREPARE alterIfNotExists;