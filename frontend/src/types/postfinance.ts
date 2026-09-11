export type PostFinancePaymentMethod = {
  id: number
  name?: string
  resolvedTitle?: Record<string, string>
  resolvedImageUrl?: string | null
  // ONSITE = card fields collected inline in the iframe; OFFSITE = the customer is
  // redirected to PostFinance's hosted page to enter the card after clicking pay.
  dataCollectionType?: 'ONSITE' | 'OFFSITE' | string
}

export type PostFinanceIframeSession = {
  paiement: {
    id_paiement: number
    id_commande: number
    reference_externe: string
    montant_chf: number
    statut: string
  }
  transaction_id?: string | null
  javascript_url?: string | null
  payment_methods: PostFinancePaymentMethod[]
  local_mode?: boolean
  error?: string | null
}

export type PostFinanceValidationResult = {
  success: boolean
  errors?: string[]
}

export type PostFinanceIframeHandler = {
  setValidationCallback: (callback: (result: PostFinanceValidationResult) => void) => void
  setInitializeCallback: (callback: () => void) => void
  setHeightChangeCallback: (callback: (height: number) => void) => void
  setReplacePrimaryActionCallback: (callback: (label: string) => void) => void
  setResetPrimaryActionCallback: (callback: () => void) => void
  create: (containerId: string) => void
  validate: () => void
  submit: () => void
  trigger: () => void
  destroy?: () => void
}

export type PostFinanceIframeCheckoutHandlerFactory = {
  (paymentMethodConfigurationId: number): PostFinanceIframeHandler
  configure: (key: string, value: boolean) => void
}
