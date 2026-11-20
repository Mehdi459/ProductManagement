"""Calcul du prix de vente (ebook, broché, formation) et des redevances estimées.

Les barèmes ci-dessous sont des approximations publiques (KDP, Udemy) à vérifier
avant publication : ils changent régulièrement. Ils sont centralisés ici pour être
faciles à ajuster.
"""
from __future__ import annotations

import math

# Prix médians de référence (€) par genre si aucune étude de marché n'est disponible.
BASE_PRICES = {
    #                        ebook, broché
    "roman": (4.99, 16.90),
    "thriller": (4.99, 17.90),
    "fantasy": (5.99, 19.90),
    "essai": (7.99, 19.90),
    "guide": (8.99, 22.90),
    "developpement_personnel": (6.99, 18.90),
    "business": (9.99, 24.90),
    "jeunesse": (3.99, 13.90),
    "biographie": (6.99, 21.90),
    "cuisine": (7.99, 24.90),
}

# Coût d'impression KDP approximatif (Amazon.fr), en €.
PRINT_FIXED_BW, PRINT_PER_PAGE_BW = 0.75, 0.012
PRINT_FIXED_COLOR, PRINT_PER_PAGE_COLOR = 0.75, 0.045
KDP_PAPERBACK_ROYALTY = 0.60
KDP_EBOOK_70 = (2.99, 9.99)      # fourchette ouvrant droit à 70 % de redevance
EBOOK_DELIVERY_PER_MB = 0.12     # frais de livraison KDP (option 70 %)

UDEMY_SHARE_MARKETPLACE = 0.37   # vente via la place de marché Udemy
UDEMY_SHARE_INSTRUCTOR = 0.97    # vente via votre lien/coupon d'instructeur
UDEMY_TIERS = [19.99, 24.99, 29.99, 34.99, 39.99, 44.99, 49.99, 54.99, 59.99, 64.99, 69.99,
               74.99, 79.99, 84.99, 89.99, 94.99, 99.99, 109.99, 119.99, 129.99, 139.99,
               149.99, 159.99, 179.99, 199.99]


def psychological(price: float, ending: float = 0.99) -> float:
    """Arrondit à un prix « psychologique » (x,99 ou x,90)."""
    return max(ending, math.floor(price) + ending)


def print_cost(pages: int, couleur: bool = False) -> float:
    fixed, per = (PRINT_FIXED_COLOR, PRINT_PER_PAGE_COLOR) if couleur else (PRINT_FIXED_BW, PRINT_PER_PAGE_BW)
    return round(fixed + per * max(24, pages), 2)


def _median(market: dict | None, key: str) -> float | None:
    try:
        v = float((market or {}).get("prix_constates", {}).get(key, {}).get("median") or 0)
        return v or None
    except (TypeError, ValueError, AttributeError):
        return None


def compute_prices(
    genre: str,
    pages: int,
    couleur: bool = False,
    duree_formation_min: int = 0,
    market: dict | None = None,
    taille_ebook_mo: float = 2.0,
) -> dict:
    base_ebook, base_broche = BASE_PRICES.get(genre, (5.99, 18.90))
    base_ebook = _median(market, "ebook") or base_ebook
    base_broche = _median(market, "broche") or base_broche

    # Plus le livre est épais, plus la valeur perçue est haute (référence : 250 pages).
    facteur = max(0.75, min(1.5, (pages / 250) ** 0.35))

    # --- ebook ---
    ebook = psychological(base_ebook * facteur)
    ebook = min(max(ebook, KDP_EBOOK_70[0]), KDP_EBOOK_70[1])
    roy_ebook = round(ebook / 1.055 * 0.70 - EBOOK_DELIVERY_PER_MB * taille_ebook_mo, 2)  # TVA livre 5,5 %

    # --- broché ---
    cout = print_cost(pages, couleur)
    plancher = (cout / KDP_PAPERBACK_ROYALTY) * 1.6  # marge minimale saine
    broche = psychological(max(base_broche * facteur, plancher), 0.90)
    roy_broche = round(broche / 1.055 * KDP_PAPERBACK_ROYALTY - cout, 2)

    # --- formation Udemy ---
    heures = duree_formation_min / 60
    cible = 29.99 if heures < 1 else 49.99 if heures < 3 else 89.99 if heures < 6 else 129.99
    base_udemy = _median(market, "formation_udemy")
    if base_udemy:
        cible = (cible + base_udemy) / 2
    udemy = min(UDEMY_TIERS, key=lambda t: abs(t - cible))

    return {
        "ebook": {"prix": ebook, "redevance_par_vente": roy_ebook, "taux": "70 %"},
        "broche": {"prix": broche, "cout_impression": cout, "redevance_par_vente": roy_broche, "taux": "60 % - impression"},
        "udemy": {
            "prix_catalogue": udemy,
            "revenu_vente_marketplace": round(udemy * UDEMY_SHARE_MARKETPLACE, 2),
            "revenu_vente_coupon_instructeur": round(udemy * UDEMY_SHARE_INSTRUCTOR, 2),
            "note": "Udemy applique souvent des promotions : le prix réellement payé est fréquemment 10-20 €.",
        },
        "skillshare": {"modele": "abonnement", "note": "Rémunération au temps de visionnage, pas de prix par cours."},
        "pages_estimees": pages,
        "avertissement": "Barèmes indicatifs à vérifier (KDP, Udemy). En France, le prix du livre est unique (loi Lang) : "
                         "le prix fixé s'applique à tous les revendeurs.",
    }


def scenarios(prices: dict, ventes_mensuelles: tuple[int, int, int] = (20, 100, 500)) -> list[dict]:
    """Projection de revenus mensuels (prudent / moyen / succès)."""
    out = []
    for nom, n in zip(("prudent", "moyen", "succès"), ventes_mensuelles):
        out.append({
            "scenario": nom,
            "ventes_ebook": n,
            "ventes_broche": n // 3,
            "eleves_udemy": n // 5,
            "revenu_mensuel_eur": round(
                n * prices["ebook"]["redevance_par_vente"]
                + (n // 3) * prices["broche"]["redevance_par_vente"]
                + (n // 5) * prices["udemy"]["revenu_vente_marketplace"] * 0.4,  # promos Udemy
                2,
            ),
        })
    return out
