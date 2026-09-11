import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Politique de confidentialité — Caribooks',
  description: 'Politique de confidentialité et protection des données personnelles (RGPD / LPD).',
}

export default function ConfidentialitePage() {
  return (
    <div style={{ maxWidth: 760, margin: '0 auto', padding: '32px 0' }}>
      <h1>Politique de confidentialité</h1>
      <p className="muted">Dernière mise à jour : juin 2026</p>

      <h2>1. Responsable du traitement</h2>
      <p>
        Le responsable du traitement des données personnelles est{' '}
        <strong>Caribooks</strong>, entreprise individuelle (personne physique), adresse complète
        communiquée sur demande par e-mail, Suisse.
      </p>
      <p>
        Contact délégué à la protection des données (DPD) :{' '}
        <a href="mailto:alexandre.rey@estiam.com">alexandre.rey@estiam.com</a>
      </p>

      <h2>2. Données collectées</h2>
      <p>Nous collectons les données suivantes :</p>
      <ul>
        <li>
          <strong>Données d&apos;identification</strong> : nom, prénom, adresse e-mail, identifiant
          Google (si connexion via Google)
        </li>
        <li>
          <strong>Données de livraison</strong> : adresse postale, numéro de téléphone
        </li>
        <li>
          <strong>Données de transaction</strong> : historique de commandes, montants, références
          de paiement
        </li>
        <li>
          <strong>Données techniques</strong> : adresse IP, logs de connexion, données de
          navigation (cookies de session)
        </li>
      </ul>

      <h2>3. Finalités et bases légales</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
            <th style={{ textAlign: 'left', padding: '8px 4px' }}>Finalité</th>
            <th style={{ textAlign: 'left', padding: '8px 4px' }}>Base légale (RGPD)</th>
          </tr>
        </thead>
        <tbody>
          {[
            ['Gestion des commandes et paiements', 'Exécution du contrat (art. 6.1.b)'],
            ['Création et gestion du compte utilisateur', 'Exécution du contrat (art. 6.1.b)'],
            ['Authentification via Google OAuth', 'Consentement (art. 6.1.a)'],
            ['Envoi de confirmations de commande', 'Exécution du contrat (art. 6.1.b)'],
            ['Obligations légales (comptabilité, fiscalité)', 'Obligation légale (art. 6.1.c)'],
            ['Amélioration du service (analytics)', 'Intérêt légitime (art. 6.1.f)'],
          ].map(([finalite, base]) => (
            <tr key={finalite} style={{ borderBottom: '1px solid var(--color-border)' }}>
              <td style={{ padding: '8px 4px' }}>{finalite}</td>
              <td style={{ padding: '8px 4px' }}>{base}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>4. Durée de conservation</h2>
      <ul>
        <li>Données de compte actif : durée de la relation contractuelle + 3 ans</li>
        <li>Données de commande : 10 ans (obligation légale comptable)</li>
        <li>Logs techniques : 12 mois</li>
        <li>Cookies de consentement : 13 mois maximum</li>
      </ul>

      <h2>5. Destinataires des données</h2>
      <p>
        Vos données sont traitées par Caribooks et ses sous-traitants techniques nécessaires à
        l&apos;exécution du service :
      </p>
      <ul>
        <li>
          <strong>PostFinance SA</strong> — traitement des paiements (Suisse)
        </li>
        <li>
          <strong>Google LLC</strong> — authentification OAuth (États-Unis — transfert encadré
          par les clauses contractuelles types UE)
        </li>
        <li>
          <strong>Internet Archive (OpenLibrary)</strong> — récupération des métadonnées
          bibliographiques par ISBN (États-Unis)
        </li>
        <li>
          <strong>Vercel Inc.</strong> — hébergement frontend (États-Unis — transfert encadré par
          les clauses contractuelles types UE)
        </li>
      </ul>
      <p>Aucune vente ou location de vos données à des tiers n&apos;est effectuée.</p>

      <h2>6. Cookies</h2>
      <p>Nous utilisons les types de cookies suivants :</p>
      <ul>
        <li>
          <strong>Cookies strictement nécessaires</strong> : jeton d&apos;authentification (JWT
          stocké en localStorage), préférences de consentement — aucun consentement requis
        </li>
        <li>
          <strong>Cookies analytiques</strong> : Vercel Speed Insights — collecte anonymisée —
          soumis à votre consentement
        </li>
      </ul>
      <p>
        Vous pouvez gérer vos préférences à tout moment via la bannière de cookies ou les
        paramètres de votre navigateur.
      </p>

      <h2>7. Vos droits (RGPD / LPD)</h2>
      <p>
        Conformément au Règlement Général sur la Protection des Données (RGPD) et à la Loi fédérale
        suisse sur la protection des données (LPD), vous disposez des droits suivants :
      </p>
      <ul>
        <li>Droit d&apos;accès à vos données personnelles</li>
        <li>Droit de rectification des données inexactes</li>
        <li>Droit à l&apos;effacement (&laquo;&nbsp;droit à l&apos;oubli&nbsp;&raquo;)</li>
        <li>Droit à la portabilité des données</li>
        <li>Droit d&apos;opposition au traitement</li>
        <li>Droit de retrait du consentement à tout moment</li>
      </ul>
      <p>
        Pour exercer ces droits, contactez notre DPD à{' '}
        <a href="mailto:alexandre.rey@estiam.com">alexandre.rey@estiam.com</a>. Nous répondrons dans un délai de 30 jours.
      </p>
      <p>
        Vous pouvez également déposer une réclamation auprès du{' '}
        <a
          href="https://www.edoeb.admin.ch"
          target="_blank"
          rel="noopener noreferrer"
        >
          Préposé fédéral à la protection des données et à la transparence (PFPDT)
        </a>
        .
      </p>

      <h2>8. Sécurité</h2>
      <p>
        Nous mettons en œuvre des mesures techniques et organisationnelles appropriées pour
        protéger vos données : chiffrement des communications (HTTPS/TLS), hachage des mots de
        passe (bcrypt), tokens JWT à durée de vie limitée, accès restreint aux données
        sensibles.
      </p>

      <h2>9. Modifications</h2>
      <p>
        Nous pouvons mettre à jour cette politique à tout moment. La date de dernière mise à jour
        est indiquée en haut de la page. En cas de modification substantielle, nous vous en
        informerons par e-mail.
      </p>

      <h2>10. Contact</h2>
      <p>
        <strong>Caribooks</strong> — entreprise individuelle (personne physique)
        <br />
        Adresse complète communiquée sur demande par e-mail
        <br />
        <a href="mailto:alexandre.rey@estiam.com">alexandre.rey@estiam.com</a>
      </p>

      <hr style={{ margin: '32px 0', border: 'none', borderTop: '1px solid var(--color-border)' }} />
      <p className="muted">
        <Link href="/conditions-utilisation">Conditions d&apos;utilisation</Link>
        {' · '}
        <Link href="/">Retour à l&apos;accueil</Link>
      </p>
    </div>
  )
}
