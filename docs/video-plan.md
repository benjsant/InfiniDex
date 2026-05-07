# Plan vidéo — FusionDex-IA

Durée cible : **2 min 30** · Format : screen recording 1440×900 · Pas de voix-off obligatoire

---

## Avant de filmer

### Préparer l'environnement
- [ ] `docker compose up -d` — vérifier que tous les services sont up
- [ ] Ouvrir http://localhost:53000 dans Chrome (pas Firefox — rendu pixel plus net)
- [ ] Zoom navigateur à **110%** (Ctrl + +) — les textes seront lisibles une fois compressés
- [ ] Masquer la barre de favoris (Ctrl+Shift+B)
- [ ] Mode "Ne pas déranger" activé (désactiver les notifications)
- [ ] Fermer tous les onglets inutiles — seul onglet visible : FusionDex

### Pré-charger les pages (évite les temps de chargement à l'écran)
Ouvrir ces onglets **avant** de lancer l'enregistrement :
- [ ] `/` — Homepage
- [ ] `/pokedex` — liste, filtre Kanto par défaut
- [ ] `/pokedex/6` — Charizard (fiche bien remplie : évolutions, stats, moves)
- [ ] `/fusion/25/6` — Pikachu × Charizard (sprites customs chargés)
- [ ] `/triple-fusions` — spoiler déjà accepté (cliquer "J'accepte" à l'avance)
- [ ] `/creators` — galerie chargée page 1
- [ ] `/ai` — chat vide, provider actif confirmé

### Préparer la question IA
Taper cette question dans le champ AI **sans envoyer** avant de filmer :
> `Quelle est la meilleure fusion offensive impliquant Pikachu, et où apprendre ses meilleures capacités ?`

Elle force l'agent à enchaîner `get_pokemon` → `get_fusion` → `search_move` → `get_move_tutors` — plusieurs tool calls visibles.

---

## Script de tournage

### Bloc 1 — Hook (0:00 → 0:20)
**Objectif : accrocher immédiatement sans intro**

| Action | Ce qu'on voit |
|--------|---------------|
| Ouvrir directement `/fusion/25/6` | Sprite Pikachu × Charizard plein écran |
| Laisser 3 secondes | Sprite custom, types Electric/Fire, stats affichées |
| Survoler le sprite inversé | Charizard × Pikachu apparaît |
| Cliquer sur le badge créateur | Modal créateur s'ouvre avec ses autres sprites |
| Fermer la modal | |

**Overlay texte à ajouter au montage :**
> *"176 000 fusions possibles. Chacune avec ses propres sprites, stats et moveset."*

---

### Bloc 2 — Pokédex (0:20 → 0:50)
**Objectif : montrer la richesse des données**

| Action | Ce qu'on voit |
|--------|---------------|
| Naviguer vers `/pokedex` | Grille 6 colonnes, 501 Pokémon |
| Cliquer filtre "Fire" dans le dropdown type | Grille se filtre, compteur mis à jour |
| Cliquer sur Charizard | Transition vers `/pokedex/6` |
| Onglet **Stats** (déjà actif) | 6 barres colorées, total visible |
| Cliquer onglet **Faiblesses** | Grille ×2 / ×½ / ×0 avec types colorés |
| Cliquer onglet **Capacités** | Table avec types, puissance, PP |
| Cliquer onglet **Évolutions** | Chaîne Charmander → Charmeleon → Charizard |

**Overlay texte :**
> *"572 Pokémon · 676 capacités · 178 talents · données extraites du jeu"*

---

### Bloc 3 — Fusion (0:50 → 1:20)
**Objectif : montrer le calculateur et ce qui rend une fusion unique**

| Action | Ce qu'on voit |
|--------|---------------|
| Naviguer vers `/fusion` | Sélecteur vide |
| Choisir **Umbreon** (head) dans le dropdown | Sprite Umbreon, types Dark |
| Taper "bulb" dans le dropdown body | Recherche filtrée → Bulbasaur |
| Choisir **Bulbasaur** (body) | Bouton "Fusionner Umbreon + Bulbasaur" activé |
| Cliquer le bouton | Transition vers résultat |
| Montrer les sprites (normal + inversé) | Types, créateur badge |
| Scroller vers les stats | Barres fusionnées |
| Cliquer bouton **swap** (↔) | Les sprites s'inversent, stats changent |

**Overlay texte :**
> *"Chaque combinaison head/body donne une fusion différente — types, stats et moveset distincts"*

---

### Bloc 4 — Assistant IA (1:20 → 2:00)
**Objectif : moment le plus impressionnant — à filmer en continu sans coupure**

| Action | Ce qu'on voit |
|--------|---------------|
| Naviguer vers `/ai` | Chat vide, 4 suggestions, provider affiché |
| Montrer les suggestions 2 secondes | Exemples de questions visibles |
| Coller/taper la question préparée | Champ de saisie rempli |
| Appuyer Entrée | Envoi |
| **Ne pas couper** — laisser tourner | Tool calls apparaissent un à un : "Base de données" → "Base de données" → "Tuteurs" |
| Laisser la réponse se terminer | Réponse complète avec stats formatées, sources affichées |

**Overlay texte (pendant les tool calls) :**
> *"L'agent interroge la base en temps réel — aucune hallucination possible"*

**Overlay texte (sur la réponse finale) :**
> *"Réponse sourcée · fail-closed · cascade DB → Wiki → Web"*

---

### Bloc 5 — Survol rapide (2:00 → 2:20)
**Objectif : montrer l'étendue sans s'attarder**

| Action | Durée | Ce qu'on voit |
|--------|-------|---------------|
| `/triple-fusions` → déplier Zapmolcuno | 8s | Sprite + types IF exclusifs (gradient) |
| `/creators` | 6s | Grille des 7081 créateurs |
| Cliquer un créateur populaire | 6s | Modal avec ses dizaines de sprites |

---

### Bloc 6 — Slide de clôture (2:20 → 2:30)
**Objectif : laisser une trace mémorable**

Afficher une slide simple (fond sombre `#090c1a`) avec :

```
FusionDex-IA

FastAPI · PostgreSQL · Next.js 15 · DeepSeek

572 Pokémon · 176 000 fusions · 9 outils IA
Code open-source → github.com/benjsant/FusionDex-IA
```

---

## Montage

### Logiciel recommandé
- **DaVinci Resolve** (gratuit, pro) — timeline, overlays texte, transitions
- **CapCut Desktop** (gratuit, rapide) — si tu veux aller vite

### Overlays texte
- Police : **Inter** ou **Geist** (cohérent avec l'UI)
- Couleur texte : blanc `#ffffff` ou doré `#e8b84b`
- Fond texte : noir semi-transparent `rgba(0,0,0,0.6)`
- Durée d'affichage : 2-3 secondes par overlay, fondu enchaîné

### Transitions
- Coupes nettes entre les blocs (pas de fondu — trop lent pour LinkedIn)
- Éventuel zoom doux sur les zones clés (DevTools → zoom viewport ou zoom montage)

### Musique (optionnel)
- [pixabay.com/music](https://pixabay.com/music/) — licence libre, chercher "lo-fi" ou "tech"
- Volume à 15-20% — l'UI doit rester lisible visuellement

---

## Checklist finale avant export

- [ ] Durée totale ≤ 2 min 30
- [ ] Résolution export : **1080p minimum** (1920×1080 ou 2560×1440)
- [ ] Les tool calls IA sont lisibles à l'écran
- [ ] Le slide de clôture reste 8-10 secondes minimum
- [ ] Pas de notifications système visibles
- [ ] Lien GitHub visible sur le slide final

---

## Post LinkedIn associé

**Format recommandé :** Vidéo native uploadée directement (pas YouTube) + texte court

**Structure du texte :**
```
Ligne 1 — accroche chiffrée (sans emoji ou 1 max)
Ligne 2 — vide
Lignes 3-6 — 4 bullets de ce que fait le projet
Ligne 7 — vide
Call to action + lien GitHub
```

**Exemple :**
```
J'ai passé 3 mois à construire un Pokédex IA pour un jeu de fan.

Voilà ce que ça donne :

→ 572 Pokémon, 176 000 fusions, chacune avec stats et moveset calculés
→ Agent IA tool-calling : interroge la base en temps réel, jamais d'hallucination
→ 9 outils enchaînés : DB → Wiki IF → DuckDuckGo en dernier recours
→ 7 081 créateurs de sprites référencés avec galerie dédiée

Stack : FastAPI · PostgreSQL · Next.js 15 · DeepSeek

Code open-source : github.com/benjsant/FusionDex-IA
```

**Hashtags (en commentaire, pas dans le post) :**
`#Python #FastAPI #NextJS #IA #OpenSource #SideProject`
