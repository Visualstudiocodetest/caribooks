export type BookRead = {
  id_article: number
  id_type_objet: number
  id_etat_usure: number
  titre: string
  isbn: string
  auteur: string | null
  editeur: string | null
  date_publication: string | null
  langue: string | null
  description: string | null
  image_link: string | null
  prix_chf: number
  actif: boolean
  date_creation: string
  categorie_ids: number[]
  etat_libelle?: string | null
  categorie_libelles?: string[]
}

export type BookCreate = Omit<BookRead, 'id_article' | 'date_creation' | 'categorie_ids' | 'categorie_libelles' | 'etat_libelle'> & {
  id_type_objet?: number
  id_etat_usure?: number
}

export type LoginRequest = {
  username: string
  password: string
}

export type Token = {
  access_token: string
  token_type: 'bearer'
}

export type UserRead = {
  id_utilisateur: number
  nom: string
  prenom: string
  email: string
  role: string
  billing_address_line1?: string | null
  billing_address_line2?: string | null
  billing_postal_code?: string | null
  billing_city?: string | null
  billing_country?: string | null
  billing_phone?: string | null
}

export type UserCreate = {
  nom: string
  prenom: string
  email: string
  mot_de_passe: string
  role?: string
  billing_address_line1?: string
  billing_address_line2?: string
  billing_postal_code?: string
  billing_city?: string
  billing_country?: string
  billing_phone?: string
}

export type UserUpdate = Partial<UserCreate & { mot_de_passe?: string }>

export type CommandeCreate = {
  numero_commande: string
  montant_total_chf: number
  statut: string
  shipping_method?: 'POST' | 'CLICK_COLLECT'
  frais_port_chf?: number
}

export type CommandeRead = CommandeCreate & {
  id_commande: number
  id_utilisateur: number
  date_commande: string
  date_creation?: string  // alias for date_commande
  cart_expires_at?: string | null
}

export type LigneCommandeCreate = {
  id_commande: number
  id_article: number
  quantite: number
  prix_unitaire_chf: number
}

export type LigneCommandeRead = LigneCommandeCreate & {
  id_ligne_commande: number
}

export type LigneCommandeAdminRead = LigneCommandeRead & {
  titre_article?: string | null
  sku_article?: string | null
}

export type CommandeAdminRead = CommandeRead & {
  client_nom?: string | null
  client_prenom?: string | null
  client_email?: string | null
  client_adresse?: string | null
}

export type PaiementCreate = {
  id_commande: number
  fournisseur_paiement?: string
  reference_externe: string
  montant_chf: number
  devise?: 'CHF'
  statut: string
  date_paiement?: string | null
}

export type PaiementRead = PaiementCreate & {
  id_paiement: number
}

export type PaiementUpdate = Partial<Omit<PaiementCreate, 'id_commande'>>

export type ScanISBNCreate = {
  id_article_livre: number
  isbn_lu: string
  valide?: boolean
}

export type ScanISBNRead = {
  id_scan_isbn: number
  id_utilisateur: number
  id_article_livre: number
  isbn_lu: string
  valide: boolean
  date_scan: string
}

export type Stock = {
  id_stock: number
  id_article: number
  id_source_stock: number
  quantite_disponible: number
  quantite_reservee?: number
  date_creation: string
}

