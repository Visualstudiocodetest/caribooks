-- Migration: add billing address fields to utilisateur and shipping fields to commande

ALTER TABLE utilisateur
  ADD COLUMN billing_address_line1 VARCHAR(255) NULL,
  ADD COLUMN billing_address_line2 VARCHAR(255) NULL,
  ADD COLUMN billing_postal_code VARCHAR(30) NULL,
  ADD COLUMN billing_city VARCHAR(100) NULL,
  ADD COLUMN billing_country VARCHAR(100) NULL,
  ADD COLUMN billing_phone VARCHAR(50) NULL;

ALTER TABLE commande
  ADD COLUMN shipping_method VARCHAR(50) NOT NULL DEFAULT 'POST',
  ADD COLUMN frais_port_chf DECIMAL(10,2) NOT NULL DEFAULT 0.00;
