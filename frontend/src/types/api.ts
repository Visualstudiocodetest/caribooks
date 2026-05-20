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
}

export type UserCreate = {
  nom: string
  prenom: string
  email: string
  mot_de_passe: string
  role?: string
}

export type CommandeCreate = {
  numero_commande: string
  montant_total_chf: number
  statut: string
}

export type CommandeRead = CommandeCreate & {
  id_commande: number
  id_utilisateur: number
  date_commande: string
}

export type LigneCommandeCreate = {
  id_commande: number
  id_article: number
  quantite: number
  prix_unitaire_chf: number
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

