# Data files for Vampire Survivors and each DLC.

## Fields description for main files
### Default stats
1. amount (weapon, powerup, limit, character) - int
2. area (weapon, powerup, limit, character) - float - in percent (default = 1 = 100%)
3. armor (powerup, character) - int
4. chance (weapon, limit) - float - in percent (default = 1 = 100%)
5. cooldown (powerup, limit, character) - float - in percent (default = 1 = 100%)
6. critChance (weapon, limit) - float - in percent (default = 1 = 100%)
7. critMul (weapon) - float - in percent (default = 1 = 100%)
8. curse (powerup, character) - float - in percent (default = 1 = 100%)
9. duration
   1. weapon - float - in milliseconds (1 sec = 1000 ms)
   2. powerup, character - float - in percent (default = 1 = 100%)
   3. limit - float - in milliseconds (1 sec = 1000 ms); in limit break description - +100 ms = +10%
10. greed (powerup, character) - float - in percent (default = 1 = 100%)
11. growth (powerup, character) - float - in percent (default = 1 = 100%)
12. hitBoxDelay (weapon) - float - in milliseconds (1 sec = 1000 ms)
13. interval (weapon) - float - in milliseconds (1 sec = 1000 ms); negative
14. luck (powerup, character) - float - in percent (default = 1 = 100%)
15. magnet (powerup, character) - float - in percent (default = 1 = 100%); multiplicative
16. maxHP
    1. powerup - float - in percent (default = 1 = 100%); multiplicative
    2. character - float - direct number (default = 100)
17. moveSpeed (weapon, powerup, character) - float - in percent (default = 1 = 100%)
18. penetrating (weapon, limit) - int
19. power
    1. weapon, limit - damage = value * 10
    2. powerup, character - float - in percent (default = 1 = 100%)
20. regen (powerup, character) - float - direct number (+ hp/sec)
21. repeatInterval (weapon) - float - in milliseconds (1 sec = 1000 ms)
22. revivals (powerup, character) - int
23. speed (weapon, powerup, limit, character) - float - in percent (default = 1 = 100%)
24. charge, charges (weapon) - int
25. revivals, rerolls, skips, banish (character) - int
26. hitsWalls (weapon) - bool
27. knockback (weapon) - float
28. charm (powerup) - float
29. fever (powerup) - float
30. bounces (weapon) - int

### Weapon
* List of levels. First entry:
  1. level - always 1
  2. name - str - english name for weapon, may **not** be equal to lang files
  3. description - str - english description for weapon, may **not** be equal to lang files
  4. tips - str - english tips for weapon, may **not** be equal to lang files
  5. texture - str - name of png sprite atlas that contains weapon's
  6. frameName - str - name of sprite in 'texture' atlas.
  7. collectionFrame - name of weapon frame for collection page (in UI.png)
  8. evoSynergy - list - list of weapons that required to evolve this weapon
  9. requires - list - list of weapons that required for this evolution
  10. requiresMax - list - list of weapons that required max level for this evolution
  11. evoInto - str - evolution of this weapon
  12. sealable - bool - can be sealed in collection
  13. bulletType - str - projectile type
  14. price - int - price in merchant
  15. isPowerUp - bool
  16. displayAsPassive - bool
  17. canCrit - bool
  18. dropRateAffectedByLuck - bool
  19. isSpecialOnly - bool - cannot appear in circumstances (i.e. level up)
  20. isEvolution - bool
* Other entries of levels describe changes to stats.

### Character
* List of levels. First entry:
  1. level - always 1
  2. prefix, charName, surname - str - full name of character, may **not** be equal to lang files
  3. description - str - description of character, may **not** be equal to lang files
  4. skins (and in main entry)
     1. startingWeapon - str - id of starting weapon (can be also 0 or VOID)
     2. skinType - str - id of skin
     3. name - str - name of skin
     4. suffix - str - additional string showing in select screen
     5. textureName - str - name of png sprite atlas for this char
     6. spriteName - str - name of sprite in 'textureName' atlas.
     7. walkingFrames - int - total number of walking frames
     8. walkFrameRate - int - _default frame rate_ = 6, each frame duration = 1000 ms / walkFrameRate
     9. charSelTexture - str - name of png sprite atlas for selection picture
     10. charSelFrame - name of sprite in 'charSelTexture' atlas.
     11. spriteAnims - dict
         1. meleeAttack, specialAnimation, idleAnimation - dict of 'skins' - animations for different character states
  5. portraitName - name of png of small square icon (in UI.png)
  6. price - int
  7. bgm - str - id of default music
  8. hiddenWeapons - list - list of id of weapons that are hidden but working as normal
  9. onEveryLevelUp - dict - stats changes on every level up 
  10. noHurt - bool - if character is invulnerable
  11. secret - bool - if secret character
* Other entries of levels describe changes to stats.
  