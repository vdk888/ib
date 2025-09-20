# Multi broker order routing

## Système de routage multi-broker

Actuellement, notre système d'exécution est configuré uniquement avec Interactive Brokers (IBKR). L'objectif est d'étendre notre infrastructure pour intégrer deux courtiers supplémentaires - Alpaca et [Crypto.com](http://Crypto.com) - afin d'optimiser l'exécution des ordres selon les spécificités de chaque plateforme.

### Architecture du routage multi-broker

Le système de routage intelligent doit déterminer automatiquement vers quel courtier diriger chaque ordre en fonction de plusieurs critères :

- **Type d'actif :** Router naturellement les cryptomonnaies vers [Crypto.com](http://Crypto.com), les ETF américains vers Alpaca, et les actions internationales vers IBKR
- **Capital disponible :** Prendre en compte le solde de trésorerie sur chaque compte courtier pour éviter les rejets d'ordres
- **Disponibilité des actifs :** Connaître le catalogue précis des instruments disponibles chez chaque courtier
- **Fallbacks :** Définir des alternatives de routage quand l'option privilégiée n'est pas disponible

### Implémentation technique

- **1. Enrichissement des métadonnées** - Ajouter aux tickers/poches :
    - Type d'actif précis (action US, action internationale, ETF, crypto)
    - Liste des courtiers compatibles avec priorité
    - Règles de fallback spécifiques
- **2. Création d'un mapping des actifs par courtier**
    - Base de données des instruments disponibles chez chaque courtier
    - Mise à jour régulière via les API de chaque plateforme
    - Classification des cryptomonnaies disponibles chez Alpaca (~20) vs celles exclusives à Crypto.com
- **3. Gestionnaire de capital par courtier**
    - Service de suivi du capital disponible pour chaque compte
    - Mécanisme d'estimation du capital nécessaire pour chaque paquet d'ordres
    - Simulation de routage avant exécution finale

### Algorithme de distribution des ordres

```python
def route_orders(orders, broker_balances, asset_mapping):
    """
    Algorithme de distribution des ordres par ordre de contrainte
    
    Parameters:
    - orders: liste des ordres à router
    - broker_balances: dict avec le capital disponible par broker
    - asset_mapping: dict avec les actifs disponibles par broker
    
    Returns:
    - routed_orders: dict avec les ordres routés par broker
    """
    # Trier les ordres par contrainte de disponibilité (du plus contraint au moins contraint)
    orders_by_constraint = sort_orders_by_constraint(orders, asset_mapping)
    
    routed_orders = {
        "ibkr": [],
        "alpaca": [],
        "crypto_com": []
    }
    
    for order in orders_by_constraint:
        asset_type = order["asset_type"]
        ticker = order["ticker"]
        amount = order["amount"]
        
        # Déterminer les brokers possibles par ordre de préférence
        if asset_type == "crypto":
            preferred_brokers = ["crypto_com", "alpaca"]
        elif asset_type == "etf_us":
            preferred_brokers = ["alpaca", "ibkr"]
        elif asset_type == "stock_us":
            preferred_brokers = ["alpaca", "ibkr"]
        elif asset_type == "stock_intl":
            preferred_brokers = ["ibkr"]  # Seul IBKR gère les actions internationales
        else:
            preferred_brokers = ["ibkr"]  # Fallback par défaut
        
        # Essayer chaque broker dans l'ordre de préférence
        order_routed = False
        for broker in preferred_brokers:
            # Vérifier si l'actif est disponible chez ce broker
            if ticker in asset_mapping[broker]:
                # Vérifier si le capital est suffisant
                if broker_balances[broker] >= amount:
                    routed_orders[broker].append(order)
                    broker_balances[broker] -= amount  # Mettre à jour le capital restant
                    order_routed = True
                    break
        
        # Si aucun broker ne peut exécuter l'ordre, le mettre dans un backlog
        if not order_routed:
            logging.warning(f"Ordre non exécutable pour {ticker}: capital insuffisant ou actif non disponible")
    
    return routed_orders

```

### Adaptation du processus existant

Pour intégrer ce système de routage multi-broker, les étapes 8, 9 et 10 du processus actuel devront être modifiées :

- **Étape 8 (Références courtier) :** Étendre pour interroger les trois courtiers et construire un mapping complet
- **Étape 9 (Ordres) :** Ajouter l'algorithme de routage pour distribuer les ordres selon les contraintes
- **Étape 10 (Exécution) :** Adapter pour gérer l'exécution parallèle sur différentes plateformes

### Roadmap d'implémentation

1. **Phase 1 :** Développement des connecteurs API pour Alpaca et [Crypto.com](http://Crypto.com)
2. **Phase 2 :** Création du système de mapping des actifs et enrichissement des métadonnées
3. **Phase 3 :** Implémentation de l'algorithme de routage par contraintes
4. **Phase 4 :** Tests et optimisation de la distribution du capital
5. **Phase 5 :** Déploiement et monitoring

Cette architecture permettra d'optimiser l'utilisation des différents comptes courtiers tout en respectant les contraintes spécifiques de chaque plateforme, sans nécessiter de transferts manuels de capital entre les courtiers.