# Screeners

Je déploie un système de multi-screeners pour élargir et diversifier mes sources d'opportunités d'investissement. Voici comment ça fonctionne:

- **Multiplication des sources de données:** Uncle Stock reste le socle, mais j'ajoute d'autres sources comme des listes d'ETF prédéfinies et des applications externes de scraping de données boursières.
- **Standardisation des inputs:** Chaque source, quelle que soit son origine, doit produire une liste de titres dans un format unifié qui peut être directement intégré à l'étape suivante du processus.
- **Interface commune:** Un adaptateur pour chaque source assure que les données sont correctement formatées et normalisées, permettant d'ajouter facilement de nouvelles sources à l'avenir.
- **Objectif:** Diversifier les signaux d'entrée pour capturer différentes opportunités de marché tout en maintenant un processus cohérent et robuste.

```mermaid
flowchart TD
    subgraph "Sources de Screeners"
        A1[Uncle Stock API]
        A2[Liste d'ETF prédéfinie]
        A3[App externe de scraping]
        A4[Future source...]
    end

    subgraph "Adaptateurs"
        B1[Adaptateur Uncle Stock]
        B2[Adaptateur ETF]
        B3[Adaptateur App externe]
        B4[Adaptateur générique]
    end

    C[Interface commune de screening]
    D[Format standardisé de titres]
    E[Étape 2: Construction de l'univers]

    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B4

    B1 --> C
    B2 --> C
    B3 --> C
    B4 --> C

    C --> D
    D --> E

    classDef sources fill:#f9f9f9,stroke:#333,stroke-width:1px
    classDef adaptateurs fill:#e6f7ff,stroke:#1890ff,stroke-width:1px
    classDef common fill:#f6ffed,stroke:#52c41a,stroke-width:1px

    class A1,A2,A3,A4 sources
    class B1,B2,B3,B4 adaptateurs
    class C,D,E common

```

Cette architecture permet d'intégrer des sources variées tout en maintenant la cohérence du processus global. Chaque screener peut cibler différents segments du marché ou stratégies, mais tous alimentent le même pipeline de traitement.