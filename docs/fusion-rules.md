# Règles de fusion

Pokémon Infinite Fusion combine deux Pokémon en un. Les règles suivantes sont **canoniques** dans le jeu et reproduites par le backend ([backend/services/fusion_service.py](https://github.com/benjsant/InfiniDex-IA/blob/main/backend/services/fusion_service.py) — voir aussi [Référence service](reference/services.md#fusion)).

Dans tout ce document : `head` = Pokémon dont on prend la tête, `body` = Pokémon dont on prend le corps.

## Types

La fusion hérite de **deux types** (ou un seul si les deux retombent sur le même) :

| Règle                                                                                       | Résultat                  |
| ------------------------------------------------------------------------------------------- | ------------------------- |
| `type1` = type primaire du `head`                                                          | sauf cas Normal/Flying    |
| `type2` = type **secondaire** du `body` s'il existe, sinon type primaire du `body`         |                           |
| Si `type1 == type2` → `type2 = null` (mono-type)                                           |                           |

### Cas particulier : Normal/Flying en head

Un `head` pur Normal/Flying (Pidgey, Spearow, Dodrio, …) prend **Flying** comme `type1` au lieu de Normal. C'est une règle IF officielle pour éviter de "perdre" le Flying sur la majorité des fusions avec ces oiseaux.

```text
Pidgey (Normal/Flying) head × Bulbasaur (Grass/Poison) body
  → type1 = Flying (Pidgey passe à Flying prioritaire)
  → type2 = Poison (body secondaire)
```

## Stats

Formule officielle, avec coefficients 2/1 pour head-vs-body selon la stat :

```text
HP       = (2 × HP_head    +     HP_body) // 3
Attack   = (    Atk_head   + 2 × Atk_body) // 3
Defense  = (    Def_head   + 2 × Def_body) // 3
Sp.Atk   = (2 × SpA_head   +     SpA_body) // 3
Sp.Def   = (2 × SpD_head   +     SpD_body) // 3
Speed    = (    Spe_head   + 2 × Spe_body) // 3
```

Head apporte davantage aux stats "mentales" (HP, SpAtk, SpDef), body aux stats "physiques" (Atk, Def, Speed).

## Moves

- **Level-up + TM + tutor** : union des deux movepools.
- **Egg moves** : union aussi.
- **Origine affichée** : chaque ligne indique si le move vient du head, du body, ou des deux.

## Abilities

- **Ability 1** de la fusion = ability 1 du `head`.
- **Ability 2** de la fusion = ability 2 du `body`.
- **Hidden ability** = union des deux hidden abilities (le joueur a accès aux deux).

## Move Experts

Mécanique IF exclusive : deux NPCs (Knot Island et Boon Island) enseignent des moves spéciaux **à condition** que la fusion satisfasse certaines contraintes.

### Modèle

Chaque règle est une ligne dans `move_expert_move` :

```text
required_pokemon_ids INTEGER[]   -- head OU body doit appartenir à cette liste
required_type_ids    INTEGER[]   -- tous ces types doivent être présents dans la fusion
required_move_ids    INTEGER[]   -- au moins un move en commun avec cette liste
```

Un **tableau vide** = aucune contrainte sur cet axe.

### Résolution

Pour chaque règle :

1. Si `required_pokemon_ids` n'est pas vide ET ni head.id ni body.id n'en fait partie → ❌ ligne rejetée.
2. Si `required_type_ids` n'est pas vide ET n'est pas sous-ensemble des types de la fusion → ❌.
3. Si `required_move_ids` n'est pas vide ET aucun move commun avec le movepool de la fusion → ❌.
4. Sinon → ✅ ligne acceptée : le move est débloqué à `expert_location`.

Entre lignes : **OR** — une seule ligne validée suffit pour débloquer le move à cet emplacement.

### Exemples

- **Umbreon × Bulbasaur** → moves Knot Island de type Dark (Umbreon pur Dark) + moves exigeant le Pokémon Umbreon.
- **Pikachu × Sandslash** → débloque moves Electric (Pikachu) + Ground (Sandslash).
- **Pikachu × Pikachu** → mono-Electric → toutes les règles exigeant un 2e type échouent, seules les règles mono-Electric restent.

### Endpoint

```http
GET /fusion/{head_id}/{body_id}/expert-moves
```

Réponse : liste de `FusionExpertMoveOut` avec, pour chaque move débloqué, la liste des `locations` où il peut être appris (0, 1 ou 2 entrées : `knot_island` et/ou `boon_island`), plus `prices_heart_scales` (map location → prix).

**Prix uniformes par expert** (source : wiki IF) :

- **Knot Island** : 2 Heart Scales par move
- **Boon Island** : 10 Heart Scales par move

Ces constantes sont définies dans `fusion_service.MOVE_EXPERT_PRICES_HEART_SCALES` — pas stockées en DB (dénormalisation inutile, règle métier dérivable de `expert_location`).

## Sprites

- **Sprite par défaut** : `CustomBattlers/{head_id}.{body_id}.png` sur le sidecar.
- **Variantes** : `CustomBattlers/{head_id}.{body_id}{a,b,c,…}.png` — plusieurs artistes peuvent avoir produit leur version.
- **Autogen** : si aucun custom n'existe, on peut tomber sur un sprite autogénéré (fallback visible dans le composant `FusionSprite`).
- **Crédits** : table `creator` + `fusion_sprite.creator_id`. À afficher systématiquement quand on montre une fusion.

## Références

- [Pokémon Infinite Fusion Wiki — Fusion mechanics](https://infinitefusion.fandom.com/)
- [backend/services/fusion_service.py](https://github.com/benjsant/InfiniDex-IA/blob/main/backend/services/fusion_service.py) — implémentation.
- [Référence service fusion](reference/services.md#fusion) — API auto-documentée.
- [docs/database.md#focus-move_expert_move](database.md#focus-move_expert_move) — modèle de données.
