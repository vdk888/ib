# Strategy - pocket level

## Stratégie au niveau des poches (Pocket-level strategy)

Pour chaque poche/screener, l'objectif est d'établir une stratégie robuste d'allocation basée sur les métriques propres aux actifs de cette poche. Cette stratégie doit être alignée avec le thème ou facteur dominant de la poche tout en maximisant l'information ratio.

### 1. État actuel

- **Approche de base (momentum):** Actuellement, le ranking est basé uniquement sur le momentum 180 jours pour accélérer la mise en place du système.
- **Limites actuelles:** Cette approche unidimensionnelle ne capture pas toute la richesse des données fondamentales disponibles et n'optimise pas pour le régime de marché spécifique à chaque poche.

### 2. Vision évolutive: Scoring multi-factoriel

- Scores de qualité fondamentale
    
    Développer des scores composites basés sur plusieurs métriques fondamentales pertinentes pour chaque type de poche:
    
    - **Poche Value:** P/E, P/B, EV/EBITDA, FCF Yield, dividend yield
    - **Poche Qualité:** ROE/ROIC, marge nette, stabilité des marges, croissance du FCF, dette/EBITDA
    - **Poche Momentum:** Performance relative 3M/6M/12M, révisions des estimations, surprises sur résultats
    - **Poche Low Vol:** Volatilité historique, bêta, drawdown maximum, corrélation au marché
- Adaptation au régime de marché
    
    Pour chaque poche, identifier le régime de marché actuel et ajuster les pondérations des facteurs en conséquence:
    
    - **Régimes possibles:** Croissance forte, ralentissement, récession, reprise
    - **Indicateurs de régime:** Utiliser les mêmes indicateurs que dans la stratégie interpoche (VIX, courbe des taux, PMI, indices d'inflation)
    - **Ajustement dynamique:** Surpondérer les facteurs qui ont historiquement le meilleur information ratio dans le régime détecté

### 3. Méthodologie d'implémentation

1. **Calcul des scores individuels:** Pour chaque métrique fondamentale, calculer un z-score normalisé au sein de la poche
2. **Création d'un score composite:** Combiner les z-scores avec des pondérations spécifiques au régime de marché
3. **Optimisation de l'information ratio:** Utiliser l'historique pour calibrer les pondérations optimales par régime
4. **Respect des contraintes:** Appliquer les règles de min/max (1-10%) et le nombre maximum de lignes (30)

### 4. Sources de données et solution pratique

- Options pour les données fondamentales
    
    Pour résoudre le problème des données limitées dans les backtests Uncle Stock:
    
    - **Option 1 - Bloomberg:** Enrichir les données des backtests avec Bloomberg pour les métriques fondamentales manquantes
    - **Option 2 - Proxy Uncle Stock:** Utiliser les titres des backtests comme proxy, en supposant qu'ils ont déjà été sélectionnés pour leur bon information ratio relatif au facteur dominant
    - **Option 3 - Hybride:** Commencer avec l'option 2 pour valider l'approche rapidement, puis enrichir progressivement avec l'option 1

### 5. Architecture technique

```jsx
// Pseudo-code pour l'allocation intra-poche basée sur scoring multi-factoriel
function optimizePocketAllocation(pocket, marketRegime, assetData) {
  // 1. Définir les poids des facteurs selon le régime et le thème de la poche
  const factorWeights = getFactorWeightsByRegime(pocket.theme, marketRegime);
  
  // 2. Calculer les scores pour chaque actif dans la poche
  const assetScores = [];
  
  for (const asset of pocket.assets) {
    // Récupérer les métriques fondamentales disponibles
    const metrics = assetData[asset.ticker] || {};
    
    // Calculer les z-scores par métrique
    const zScores = calculateZScores(metrics, pocket.assets);
    
    // Calculer le score composite pondéré
    const compositeScore = calculateWeightedScore(zScores, factorWeights);
    
    assetScores.push({
      ticker: asset.ticker,
      score: compositeScore,
      informationRatio: metrics.informationRatio || 0
    });
  }
  
  // 3. Trier et allouer selon les scores
  assetScores.sort((a, b) => b.score - a.score);
  
  // 4. Appliquer les contraintes (max 30 lignes, 1-10% par ligne)
  const selectedAssets = assetScores.slice(0, 30);
  const allocation = applyAllocationConstraints(selectedAssets);
  
  return allocation;
}

```

<aside>
**Approche pragmatique recommandée**

Compte tenu des contraintes actuelles sur les données détaillées:

1. Commencer par une implémentation basée sur les titres des backtests Uncle Stock, en considérant qu'ils ont déjà été pré-filtrés pour leur qualité relative au facteur dominant
2. Ajouter le momentum comme première couche d'optimisation (déjà en place)
3. Intégrer progressivement les métriques fondamentales disponibles via Bloomberg en commençant par les plus pertinentes pour chaque thème de poche
4. Valider l'approche par backtesting en mesurant l'amélioration de l'information ratio avant/après l'enrichissement des facteurs
</aside>

### 6. KPIs et monitoring

- **Information Ratio:** Mesurer l'IR de chaque poche avant/après l'implémentation du scoring multi-factoriel
- **Stabilité du portefeuille:** Turnover réduit grâce à l'approche plus robuste
- **Performance relative par régime:** Vérifier que l'adaptation au régime de marché produit les résultats escomptés
- **Qualité des données:** Taux de couverture des métriques fondamentales utilisées dans le scoring