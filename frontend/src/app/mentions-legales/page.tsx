import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Mentions légales — Caribooks',
  description: "Mentions légales de la plateforme Caribooks : éditeur, hébergement, propriété intellectuelle.",
}

export default function MentionsLegalesPage() {
  return (
    <div style={{ maxWidth: 760, margin: '0 auto', padding: '32px 0' }}>
      <h1>Mentions légales</h1>
      <p className="muted">Dernière mise à jour : juin 2026</p>

      <h2>1. Éditeur du site</h2>
      <p>
        Le site Caribooks est édité par <strong>[NOM_ENTITE_LEGALE]</strong>, [FORME_JURIDIQUE],
        dont le siège est situé au [ADRESSE_COMPLETE], Suisse.
      </p>
      <p>
        Contact : <a href="mailto:alexandre.rey@estiam.com">alexandre.rey@estiam.com</a>
      </p>
      <p>
        Caribooks est un projet réalisé dans le cadre du Titre Professionnel Concepteur
        Développeur d&apos;Applications (ESTIAM), en partenariat avec l&apos;association Caritas.
        Il ne constitue pas une activité commerciale enregistrée à ce stade.
      </p>

      <h2>2. Directeur de la publication</h2>
      <p>Alexandre REY.</p>

      <h2>3. Hébergement</h2>
      <ul>
        <li>
          <strong>Frontend (Next.js)</strong> : Vercel Inc. — 340 S Lemon Ave #4133, Walnut, CA
          91789, États-Unis — <a href="https://vercel.com" target="_blank" rel="noopener noreferrer">vercel.com</a>
        </li>
        <li>
          <strong>Backend et base de données</strong> : Oracle Cloud Infrastructure, exploité par
          Oracle Corporation — <a href="https://www.oracle.com/cloud/" target="_blank" rel="noopener noreferrer">oracle.com/cloud</a>
        </li>
      </ul>

      <h2>4. Propriété intellectuelle</h2>
      <p>
        L&apos;ensemble des éléments techniques et graphiques du site (code source, charte
        graphique, logo) est la propriété de l&apos;éditeur, sauf mention contraire. Les
        informations bibliographiques affichées (titres, auteurs, éditeurs) proviennent de{' '}
        <a href="https://openlibrary.org" target="_blank" rel="noopener noreferrer">OpenLibrary</a>{' '}
        (Internet Archive).
      </p>

      <h2>5. Protection des données personnelles</h2>
      <p>
        Le traitement des données personnelles est détaillé dans notre{' '}
        <Link href="/confidentialite">politique de confidentialité</Link>, conformément au RGPD et
        à la loi fédérale suisse sur la protection des données (LPD).
      </p>

      <hr style={{ margin: '32px 0', border: 'none', borderTop: '1px solid var(--color-border)' }} />
      <p className="muted">
        <Link href="/conditions-utilisation">Conditions d&apos;utilisation</Link>
        {' · '}
        <Link href="/confidentialite">Confidentialité</Link>
        {' · '}
        <Link href="/">Retour à l&apos;accueil</Link>
      </p>
    </div>
  )
}
