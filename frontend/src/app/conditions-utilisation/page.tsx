import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: "Conditions d'utilisation — Caribooks",
  description: "Conditions générales d'utilisation de la plateforme Caribooks.",
}

export default function ConditionsUtilisationPage() {
  return (
    <div style={{ maxWidth: 760, margin: '0 auto', padding: '32px 0' }}>
      <h1>Conditions générales d&apos;utilisation</h1>
      <p className="muted">Dernière mise à jour : juin 2026</p>

      <h2>1. Présentation du service</h2>
      <p>
        Caribooks est une plateforme de vente de livres de seconde main exploitée par{' '}
        <strong>[NOM_ENTITE_LEGALE]</strong>, [FORME_JURIDIQUE], dont le siège social est situé au{' '}
        [ADRESSE_COMPLETE], Suisse (ci-après &laquo;&nbsp;Caribooks&nbsp;&raquo;).
      </p>
      <p>
        Le service permet aux utilisateurs de parcourir le catalogue, d&apos;ajouter des articles
        au panier et d&apos;effectuer des commandes livrables exclusivement en Suisse, en francs
        suisses (CHF).
      </p>

      <h2>2. Acceptation des conditions</h2>
      <p>
        Tout accès ou utilisation du site implique l&apos;acceptation sans réserve des présentes
        conditions. Si vous n&apos;acceptez pas ces conditions, vous devez cesser d&apos;utiliser
        le service.
      </p>

      <h2>3. Création de compte</h2>
      <p>
        Pour passer commande, vous devez créer un compte en fournissant des informations exactes et
        à jour (nom, prénom, adresse e-mail). Vous pouvez vous authentifier par e-mail/mot de passe
        ou via votre compte Google. Vous êtes responsable de la confidentialité de vos
        identifiants.
      </p>

      <h2>4. Commandes et paiements</h2>
      <p>
        Les prix sont indiqués en CHF, toutes taxes comprises. Caribooks se réserve le droit de
        modifier les prix à tout moment. Les paiements sont traités de manière sécurisée par
        PostFinance. Une commande n&apos;est définitive qu&apos;après confirmation de paiement.
      </p>
      <p>
        Les frais de port sont calculés selon le mode de livraison choisi (envoi postal ou Click
        &amp; Collect à 1 CHF).
      </p>

      <h2>5. Livraison et Click &amp; Collect</h2>
      <p>
        Les livraisons sont effectuées exclusivement en Suisse. Le délai indicatif est de 3 à 5
        jours ouvrés. L&apos;option Click &amp; Collect permet de retirer votre commande
        directement auprès de [NOM_ENTITE_LEGALE] à l&apos;adresse [ADRESSE_COLLECTE].
      </p>

      <h2>6. Droit de rétractation</h2>
      <p>
        Conformément au droit suisse, les articles de seconde main vendus via cette plateforme ne
        sont pas soumis au droit de rétractation légal applicable aux biens neufs. Toutefois,
        Caribooks s&apos;engage à traiter tout litige avec bienveillance. Contactez-nous à{' '}
        <a href="mailto:[EMAIL_CONTACT]">[EMAIL_CONTACT]</a> dans les 14 jours suivant la
        réception.
      </p>

      <h2>7. Propriété intellectuelle</h2>
      <p>
        L&apos;ensemble du contenu du site (textes, images, logo) est protégé par le droit
        d&apos;auteur. Toute reproduction sans autorisation écrite préalable est interdite.
      </p>

      <h2>8. Limitation de responsabilité</h2>
      <p>
        Caribooks ne peut être tenu responsable des dommages indirects résultant de
        l&apos;utilisation du service. La responsabilité de Caribooks est limitée au montant de la
        commande concernée.
      </p>

      <h2>9. Droit applicable</h2>
      <p>
        Les présentes conditions sont soumises au droit suisse. Tout litige sera soumis à la
        juridiction exclusive des tribunaux de [CANTON], Suisse.
      </p>

      <h2>10. Contact</h2>
      <p>
        Pour toute question relative aux présentes conditions :{' '}
        <a href="mailto:[EMAIL_CONTACT]">[EMAIL_CONTACT]</a>
      </p>

      <hr style={{ margin: '32px 0', border: 'none', borderTop: '1px solid var(--color-border)' }} />
      <p className="muted">
        <Link href="/confidentialite">Politique de confidentialité</Link>
        {' · '}
        <Link href="/">Retour à l&apos;accueil</Link>
      </p>
    </div>
  )
}
