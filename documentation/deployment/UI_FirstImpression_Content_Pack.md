# UI First-Impression Content Pack — four brain pages, tray section, MEDIC citation, copy corrections

**Author:** PillSafe SA (Fable), 2026-07-30. **Builder:** Opus subagent, this session.
**Rule of the pack:** the words below are transcribed into the app **verbatim** — layout and styling
are the builder's; copy is not. Every EN key has its FR twin here; `npm run check:i18n` must end in
EN/FR lockstep. Nothing in this pack touches the backend, the sidecar, or any brain contract.

**Copy provenance:** ADR consolidated baseline + entries through 2026-07-30; CSCN8040 Assignment-4
interim report (measured numbers + pending-work list); `PillSafeTray_v2_Spec.md`;
`LLM_Rx_Parsing_RedTeam_Brief.md` §5.1 (MEDIC, primary-source verified);
`documentation/evaluation/rx_parsing/README.md`. No number below is new — each traces to one of
those sources.

---

## §0 Conventions (builder MUST follow)

1. **All copy through `t()`** — new pages contain zero hardcoded user-visible strings. Numeric stat
   values that render differently per locale (`31.1%` vs `31,1 %`) live in the locale files, NOT in
   code constants (this deliberately differs from `PrescriptionReaderPage`'s `MEASURED_ROWS`, whose
   values are locale-identical).
2. **Template:** clone the structure of `pages/public/brains/PrescriptionReaderPage.tsx` — hero with
   breadcrumb / white cards / back-to-About button. Reuse `public.brains.backToAbout`.
3. **Routes + wiring:**
   - `/about/brains/pill-vision` → `pages/public/brains/PillVisionPage.tsx`
   - `/about/brains/deterministic-matcher` → `pages/public/brains/DeterministicMatcherPage.tsx`
   - `/about/brains/monograph-retrieval` → `pages/public/brains/MonographRetrievalPage.tsx`
   - `/about/brains/answer-voice` → `pages/public/brains/AnswerVoicePage.tsx`
   - Register all four in `router/index.tsx` beside the existing prescription-reader route,
     following its exact import pattern; add `href` for `vision`, `matcher`, `retrieval`, `voice`
     in `content/fiveBrains.ts` (update its header comment — the other four are no longer "later
     sessions").
4. **Tray image:** source `D:\Projects\PillSafe\Brainstorm\PillSafeTray.png` (2.4 MB — never ship
   raw). Re-encode to JPEG quality ~85, max width 1400 px →
   `dev/frontend/src/assets/pillsafe-tray-render.jpg` (target < 300 KB; the render is flat-colour
   on white, JPEG is fine, no transparency). `<img>` gets explicit `width`/`height`,
   `loading="lazy"`, alt text from `public.brains.vision.trayImageAlt`.
5. **Builder bars (all must pass, in this order):** `npx tsc --noEmit` → `npm run check:i18n`
   (key parity + no hardcoded copy) → `npm run build`. Do NOT start the dev server; do NOT commit;
   do NOT touch files outside the list in §9.
6. **FR conventions:** vous-form; Québec `courriel`/`téléverser`; decimal comma + narrow space
   before % (`31,1 %`); space thousands separator (`7 055`); « guillemets » for quotes.

---

## §1 Copy corrections (existing keys — both locales)

| File | Key | Change |
|---|---|---|
| `en.json` | `public.science.citations.gopill.journal` | `"MDPI Mathematics 2025"` → `"MDPI Mathematics 2026"` (the verified citation is Mathematics 14(2), art. 356 — vol. 14 is 2026; Assignment-4 reference list concurs) |
| `fr.json` | same key | `"MDPI Mathematics 2025"` → `"MDPI Mathematics 2026"` |

MedSnap's venue line (`medRxiv 2020; related US patents`) is under red-team verification this
session — do NOT change it in the build pass.

---

## §2 SciencePage — MEDIC citation (new entry #6, after `gopill`, before `medsnap`)

`SciencePage.tsx` `CITATIONS` array — insert:

```js
{
  key: 'medic',
  title: 'MEDIC — Large language models for preventing medication direction errors in online pharmacies',
  url: 'https://www.nature.com/articles/s41591-024-02933-8',
},
```

(No author list is rendered because none was primary-source-verified — same convention as the
GO-PILL entry. Title is bibliographic identity: never translated.)

`en.json` → `public.science.citations.medic`:
```json
{
  "journal": "Nature Medicine 2024",
  "point": "Production evidence from an online pharmacy that a raw language model — however capable — invents and drops medication details, and that a guarded system which cross-checks every extraction against a medication catalogue and halts rather than guesses prevents more errors. The Prescription Reader's five safety guardrails are transplanted directly from this paper's design."
}
```

`fr.json` → `public.science.citations.medic`:
```json
{
  "journal": "Nature Medicine 2024",
  "point": "Preuve en production, issue d'une pharmacie en ligne, qu'un modèle de langage brut — aussi performant soit-il — invente ou omet des détails de médication, et qu'un système encadré, qui confronte chaque extraction à un catalogue de médicaments et s'arrête plutôt que de deviner, prévient davantage d'erreurs. Les cinq garde-fous de sécurité du Lecteur d'ordonnances sont directement transposés de la conception décrite dans cet article."
}
```

---

## §3 Pill Vision page — `public.brains.vision.*`

Page sections: hero → what → how (4 steps) → measured (3 stat tiles + notes) → the negative
finding → **the tray (with image)** → **pending work** → back-to-About.

### EN

```json
"vision": {
  "breadcrumb": "Pill Vision",
  "heroLead": "The second of MyPillSafe's five brains. It {{desc}}",
  "whatTitle": "What it does",
  "whatBody1": "You place a loose pill on the printed MyPillSafe capture card and photograph it. Pill Vision finds the pill in the photo, measures its colour against the card's calibration patches, classifies its shape, and reads the text pressed into its surface — twice, with two complementary methods. What comes out is not a drug name: it is an honest description — colour, shape, type, and two imprint readings, each with its own confidence.",
  "whatBody2": "That description goes to the <strong>Deterministic Matcher</strong>, which compares it against the medications on your confirmed list — never against the whole Canadian formulary. Pill Vision describes; it does not decide.",
  "howTitle": "How it works",
  "how": {
    "find": {
      "title": "1. Find the pill",
      "body": "A zero-shot segmentation model isolates the pill on the capture card. We also fine-tuned a dedicated detector on 8,560 studio pill images — and on real phone photos it missed 28% of pills, so the zero-shot model that finds them all is what shipped."
    },
    "colour": {
      "title": "2. Measure the colour",
      "body": "Colour is calculated, not learned: the card's printed patches let the app correct for your room's lighting, and the pill's corrected colour is looked up in a 13-colour palette. No training dataset gets a vote on what colour your pill is."
    },
    "shape": {
      "title": "3. Classify the shape",
      "body": "A small neural network classifies the pill's outline into 11 shapes, with a geometry rule as fallback for the rare outlines it was not trained to see."
    },
    "imprint": {
      "title": "4. Read the imprint — twice",
      "body": "The characters pressed into a pill are its strongest identifier and the hardest thing to read. Two complementary readers look at every face — one better at partial reads, and one, using contrast enhancement, about 3.5× better at exact reads. Both readings are passed on unmerged, so the matcher can weigh them honestly."
    }
  },
  "measuredTitle": "Measured performance — and what it honestly means",
  "measuredIntro": "On 180 real phone photos of 15 over-the-counter products — our development set, reported honestly as such, not a benchmark:",
  "stats": {
    "detect": { "value": "180/180", "label": "pills found in the photo" },
    "verify": { "value": "31.1%", "label": "of photos verified on the first try" },
    "fa": { "value": "1.25%", "label": "false-accept rate — the number everything is tuned to keep lowest (9 of 720 wrong-profile trials)" }
  },
  "measuredNote": "The low verification rate is deliberate. When lighting or focus makes the imprint unreadable, MyPillSafe abstains and asks you to flip the pill or retake the photo rather than gamble. Unreadable imprints cause 83.9% of those abstentions — which is exactly what the capture protocol below is designed to attack.",
  "negativeTitle": "The finding we didn't expect",
  "negativeBody": "We fine-tuned models for detection and for shape on thousands of studio pill photos, and both beat their zero-shot baselines in the studio — then lost to them on real phone photos. Studio benchmarks overstated real-world transfer on two of our three vision heads, and fine-tuning the imprint reader on its own teacher's output lost twice more. That negative result now shapes the whole pipeline, and is a core finding of the paper in preparation: zero-shot detection shipped, colour was never trained at all, and the trained shape model is the only survivor.",
  "trayTitle": "The PillSafeTray — a portable studio",
  "trayBadge": "Research prototype — in development",
  "trayBody1": "The next step in controlled capture is a wallet-size pill tray with exactly the footprint of a bank card (85.6 × 54 mm). Six shallow wells hold up to six pills, imprint up, for a single photo — a dose of seven or eight pills uses two loads. Its printed sheet carries the same calibrated colour patches as the capture card, four corner markers that tell the app exactly where the tray and every well sit in the photo, and one printed instruction: imprint UP.",
  "trayBody2": "Photographed up close with the flash forced on, the tray turns an uncontrolled phone photo into a small, repeatable studio shot. We measured why that matters: lighting — not the pill — is the dominant reason a first shot fails (12 of 29 first shots verified under a proxy of this protocol), and forced flash brings a dim evening room back to roughly daylight verification rates.",
  "trayImageAlt": "Design render of the PillSafeTray v2: a bank-card-size dark grey tray with six numbered pill wells, a calibration patch strip, corner markers and an 'imprint UP' instruction, shown next to a bank card for scale.",
  "trayImageCaption": "Design render, not a photograph. The tray body is print-ready; the confirmatory capture study is pre-registered and still ahead.",
  "pendingTitle": "What's still ahead — stated openly",
  "pendingIntro": "All modelling and development-set evaluation are complete and frozen. The confirmatory work is pre-registered and pending:",
  "pending": {
    "p1": "3D-print the tray body (the print-ready model exists) and produce its calibrated insert sheet.",
    "p2": "An 88-photo pilot to fix the capture parameters, then the pre-registered 600-photo confirmatory study with the same 15 products.",
    "p3": "Two pre-registered outcomes: usability — a correct, imprint-up pill verifies on the first photo — and safety — zero false accepts across roughly 630 stray-pill presentations, which by the rule of three would bound the true rate below 0.48%.",
    "p4": "The imprint decision: whether controlled tray capture recovers enough unreadable imprints to stay zero-shot, or whether a properly trained imprint reader — on independent, hand-keyed labels this time — is warranted.",
    "p5": "A colour-boundary refinement, starting with the white/grey split."
  }
}
```

### FR

```json
"vision": {
  "breadcrumb": "Vision des comprimés",
  "heroLead": "Le deuxième des cinq cerveaux de MyPillSafe. Il {{desc}}",
  "whatTitle": "Ce qu'il fait",
  "whatBody1": "Vous déposez un comprimé isolé sur la carte de capture imprimée MyPillSafe et vous le photographiez. La Vision des comprimés repère le comprimé sur la photo, mesure sa couleur par rapport aux pastilles d'étalonnage de la carte, classe sa forme et lit le texte gravé à sa surface — deux fois, par deux méthodes complémentaires. Ce qui en sort n'est pas un nom de médicament : c'est une description honnête — couleur, forme, type et deux lectures de l'inscription, chacune avec son propre niveau de confiance.",
  "whatBody2": "Cette description est transmise au <strong>Comparateur déterministe</strong>, qui la confronte aux médicaments de votre liste confirmée — jamais à l'ensemble du répertoire canadien. La Vision des comprimés décrit ; elle ne décide pas.",
  "howTitle": "Comment il fonctionne",
  "how": {
    "find": {
      "title": "1. Repérer le comprimé",
      "body": "Un modèle de segmentation générique (« zero-shot ») isole le comprimé sur la carte de capture. Nous avions aussi entraîné un détecteur spécialisé sur 8 560 images de studio — sur de vraies photos de téléphone, il manquait 28 % des comprimés ; c'est donc le modèle générique, qui les trouve tous, qui a été retenu.",
    },
    "colour": {
      "title": "2. Mesurer la couleur",
      "body": "La couleur est calculée, pas apprise : les pastilles imprimées de la carte permettent de corriger l'éclairage de la pièce, puis la couleur corrigée du comprimé est recherchée dans une palette de 13 couleurs. Aucun jeu de données d'entraînement n'a voix au chapitre sur la couleur de votre comprimé."
    },
    "shape": {
      "title": "3. Classer la forme",
      "body": "Un petit réseau de neurones classe le contour du comprimé parmi 11 formes, avec une règle géométrique en secours pour les contours rares qu'il n'a pas appris à reconnaître."
    },
    "imprint": {
      "title": "4. Lire l'inscription — deux fois",
      "body": "Les caractères gravés dans un comprimé sont son identifiant le plus fort et la chose la plus difficile à lire. Deux lecteurs complémentaires examinent chaque face — l'un meilleur pour les lectures partielles, l'autre, avec un rehaussement de contraste, environ 3,5× meilleur pour les lectures exactes. Les deux lectures sont transmises sans être fusionnées, pour que le comparateur puisse les peser honnêtement."
    }
  },
  "measuredTitle": "Performance mesurée — et ce qu'elle veut dire honnêtement",
  "measuredIntro": "Sur 180 vraies photos de téléphone de 15 produits en vente libre — notre ensemble de développement, présenté honnêtement comme tel, pas un banc d'essai :",
  "stats": {
    "detect": { "value": "180/180", "label": "comprimés repérés sur la photo" },
    "verify": { "value": "31,1 %", "label": "des photos vérifiées du premier coup" },
    "fa": { "value": "1,25 %", "label": "taux de fausses acceptations — le chiffre que tout est réglé pour garder au plus bas (9 essais sur 720 hors profil)" }
  },
  "measuredNote": "Le faible taux de vérification est voulu. Quand l'éclairage ou la mise au point rend l'inscription illisible, MyPillSafe s'abstient et vous demande de retourner le comprimé ou de reprendre la photo, plutôt que de parier. Les inscriptions illisibles causent 83,9 % de ces abstentions — c'est précisément ce que le protocole de capture ci-dessous vise à corriger.",
  "negativeTitle": "Le résultat que nous n'attendions pas",
  "negativeBody": "Nous avons entraîné des modèles pour la détection et pour la forme sur des milliers de photos de studio ; tous deux battaient leur référence générique en studio — puis ont perdu contre elle sur de vraies photos de téléphone. Les bancs d'essai en studio ont surestimé le transfert au réel sur deux de nos trois modules de vision, et l'entraînement du lecteur d'inscriptions sur les lectures de son propre « professeur » a perdu deux fois de plus. Ce résultat négatif façonne aujourd'hui tout le pipeline, et c'est une conclusion centrale de l'article en préparation : la détection générique a été retenue, la couleur n'a jamais été apprise, et le modèle de forme entraîné est le seul survivant.",
  "trayTitle": "Le PillSafeTray — un studio de poche",
  "trayBadge": "Prototype de recherche — en développement",
  "trayBody1": "La prochaine étape de la capture contrôlée est un plateau à comprimés au format portefeuille, exactement l'empreinte d'une carte bancaire (85,6 × 54 mm). Six alvéoles peu profondes accueillent jusqu'à six comprimés, inscription vers le haut, pour une seule photo — une prise de sept ou huit comprimés se fait en deux chargements. Sa feuille imprimée porte les mêmes pastilles de couleur étalonnées que la carte de capture, quatre repères de coin qui indiquent à l'application où se trouvent exactement le plateau et chaque alvéole sur la photo, et une seule consigne imprimée : inscription vers le HAUT.",
  "trayBody2": "Photographié de près avec le flash forcé, le plateau transforme une photo de téléphone non contrôlée en une petite prise de studio reproductible. Nous avons mesuré pourquoi cela compte : l'éclairage — pas le comprimé — est la cause dominante de l'échec d'une première photo (12 premières photos vérifiées sur 29 sous un substitut de ce protocole), et le flash forcé ramène une pièce sombre en soirée à un taux de vérification proche de la lumière du jour.",
  "trayImageAlt": "Rendu de conception du PillSafeTray v2 : un plateau gris foncé au format carte bancaire avec six alvéoles numérotées, une bande de pastilles d'étalonnage, des repères de coin et la consigne « inscription vers le haut », présenté à côté d'une carte bancaire pour l'échelle.",
  "trayImageCaption": "Rendu de conception, pas une photographie. Le corps du plateau est prêt à imprimer ; l'étude de capture confirmatoire est préenregistrée et encore à venir.",
  "pendingTitle": "Ce qui reste à faire — dit ouvertement",
  "pendingIntro": "Toute la modélisation et l'évaluation sur l'ensemble de développement sont terminées et figées. Le travail confirmatoire est préenregistré et en attente :",
  "pending": {
    "p1": "Imprimer en 3D le corps du plateau (le modèle prêt à imprimer existe) et produire sa feuille d'insertion étalonnée.",
    "p2": "Un pilote de 88 photos pour fixer les paramètres de capture, puis l'étude confirmatoire préenregistrée de 600 photos avec les mêmes 15 produits.",
    "p3": "Deux résultats préenregistrés : l'utilisabilité — un comprimé correct, inscription vers le haut, se vérifie à la première photo — et la sécurité — zéro fausse acceptation sur environ 630 présentations de comprimés étrangers, ce qui, par la règle de trois, bornerait le taux réel sous 0,48 %.",
    "p4": "La décision sur l'inscription : déterminer si la capture contrôlée sur plateau récupère assez d'inscriptions illisibles pour rester en modèle générique, ou si un lecteur d'inscriptions correctement entraîné — cette fois sur des étiquettes indépendantes saisies à la main — se justifie.",
    "p5": "Un raffinement des frontières de couleur, en commençant par la séparation blanc/gris."
  }
}
```

**NOTE (builder):** the FR `how.find` block above accidentally shows a trailing comma inside the
JSON example — locale files are strict JSON; write them without it.

---

## §4 Deterministic Matcher page — `public.brains.matcher.*`

Sections: hero → what → the formula in the open → abstaining is the design → why not identify →
frozen-by-rule note → back.

### EN

```json
"matcher": {
  "breadcrumb": "Deterministic Matcher",
  "heroLead": "The third of MyPillSafe's five brains. It is {{desc}}",
  "whatTitle": "What it does",
  "whatBody1": "The matcher receives Pill Vision's description — colour, shape, type, and two imprint readings — and compares it against each medication on your confirmed list. It returns exactly one of three outcomes: <strong>verified</strong> (this is one of your medications, and here is which attributes matched), <strong>doesn't match</strong> (this matches nothing you take — stop and check with a pharmacist), or <strong>abstain</strong> (not sure — flip the pill, retake the photo, or confirm from a short list).",
  "whatBody2": "It is deliberately not machine learning. Safety tuning needs an explicit formula that can be audited: every score can be recomputed by hand, every threshold has a written reason, and the project's own rules forbid changing any of them without re-running the full evaluation that set them.",
  "formulaTitle": "The formula, in the open",
  "formulaBody": "Each attribute contributes a weighted share of the match score: the imprint carries 55%, colour 25%, shape 15%, and type — tablet or capsule — 5%. A pill is verified only above a score of 0.70, rejected below 0.25, and everything in between — or any near-tie between two of your own medications — becomes an abstention. The imprint dominates on purpose: it is the one attribute that genuinely separates look-alike pills.",
  "abstainTitle": "Abstaining is the design, not a failure",
  "abstainBody": "On our development photos the matcher verifies roughly 17–29% of single shots and abstains on most of the rest. That trade is deliberate: the thresholds were tuned so that wrongly verifying a pill — the one outcome that could put the wrong medication in someone's mouth — is the rarest event we can measure: a 1.15% false-accept rate in held-out cross-validation, 1.25% on real photos. And when it abstains, it says what to do next: flip the pill so the other face's imprint can be read, or choose from the short list it could not separate.",
  "collisionTitle": "Why not identify against everything?",
  "collisionBody": "Because Canadian pills genuinely collide. In our reference data, 13 different products are all the same 'blue diamond tablet, imprint SIL 25' — cross-licensed generics no camera could ever tell apart. Across the 7,055 marketed Canadian tablets and capsules, even a perfect attribute description narrows to the right product only 38.4% of the time; within a five-medication personal profile, the chance of two colliding is about 0.3%. Verification against your own list is not a compromise — it is the version of the problem that can actually be done safely.",
  "frozenNote": "The exact matcher that was evaluated is the matcher that ships: its weights and thresholds are frozen, and every number above can be re-derived from the evaluation that set it."
}
```

### FR

```json
"matcher": {
  "breadcrumb": "Comparateur déterministe",
  "heroLead": "Le troisième des cinq cerveaux de MyPillSafe. C'est {{desc}}",
  "whatTitle": "Ce qu'il fait",
  "whatBody1": "Le comparateur reçoit la description produite par la Vision des comprimés — couleur, forme, type et deux lectures de l'inscription — et la confronte à chaque médicament de votre liste confirmée. Il rend exactement l'un de trois verdicts : <strong>vérifié</strong> (c'est l'un de vos médicaments, avec le détail des attributs concordants), <strong>ne correspond pas</strong> (cela ne correspond à rien de ce que vous prenez — arrêtez-vous et vérifiez auprès d'un pharmacien), ou <strong>abstention</strong> (incertain — retournez le comprimé, reprenez la photo ou confirmez à partir d'une courte liste).",
  "whatBody2": "Ce n'est délibérément pas de l'apprentissage automatique. Le réglage de sécurité exige une formule explicite et vérifiable : chaque score peut être recalculé à la main, chaque seuil a une justification écrite, et les règles du projet interdisent d'en modifier un sans relancer l'évaluation complète qui l'a fixé.",
  "formulaTitle": "La formule, au grand jour",
  "formulaBody": "Chaque attribut apporte une part pondérée du score de correspondance : l'inscription compte pour 55 %, la couleur pour 25 %, la forme pour 15 % et le type — comprimé ou gélule — pour 5 %. Un comprimé n'est vérifié qu'au-dessus d'un score de 0,70, rejeté sous 0,25, et tout l'entre-deux — ou toute quasi-égalité entre deux de vos propres médicaments — devient une abstention. L'inscription domine à dessein : c'est le seul attribut qui distingue réellement les comprimés qui se ressemblent.",
  "abstainTitle": "L'abstention est un choix de conception, pas un échec",
  "abstainBody": "Sur nos photos de développement, le comparateur vérifie environ 17 à 29 % des prises uniques et s'abstient sur la plupart des autres. Ce compromis est voulu : les seuils ont été réglés pour que la vérification erronée d'un comprimé — le seul verdict qui pourrait mettre le mauvais médicament dans la bouche de quelqu'un — soit l'événement le plus rare que nous puissions mesurer : un taux de fausses acceptations de 1,15 % en validation croisée, de 1,25 % sur photos réelles. Et quand il s'abstient, il dit quoi faire ensuite : retourner le comprimé pour lire l'inscription de l'autre face, ou choisir dans la courte liste qu'il n'a pas pu départager.",
  "collisionTitle": "Pourquoi ne pas identifier parmi tout le répertoire ?",
  "collisionBody": "Parce que les comprimés canadiens se confondent réellement. Dans nos données de référence, 13 produits différents sont tous le même « comprimé bleu en losange, inscription SIL 25 » — des génériques sous licences croisées qu'aucune caméra ne pourrait distinguer. Sur les 7 055 comprimés et gélules commercialisés au Canada, même une description parfaite des attributs ne désigne le bon produit que 38,4 % du temps ; au sein d'un profil personnel de cinq médicaments, la probabilité d'une collision est d'environ 0,3 %. Vérifier par rapport à votre propre liste n'est pas un pis-aller — c'est la version du problème qui peut réellement être résolue en sécurité.",
  "frozenNote": "Le comparateur évalué est exactement celui qui est livré : ses pondérations et ses seuils sont figés, et chaque chiffre ci-dessus peut être retracé jusqu'à l'évaluation qui l'a fixé."
}
```

---

## §5 Monograph Retrieval page — `public.brains.retrieval.*`

Sections: hero → what → how (4 steps) → what it refuses → back.

### EN

```json
"retrieval": {
  "breadcrumb": "Monograph Retrieval",
  "heroLead": "The fourth of MyPillSafe's five brains. It {{desc}}",
  "whatTitle": "What it does",
  "whatBody1": "When you ask a question, Monograph Retrieval finds the passages that answer it — from the official Health Canada product monograph of your medication, never from the open internet. Behind it sits a corpus of 6,803 product monographs, plus 27 ingredient documents covering common shelf products that have no monograph of their own, split into 3.9 million searchable passages.",
  "whatBody2": "Its defining rule is that retrieval is <strong>scoped to one product</strong>. The system first resolves which product you are asking about, and then searches only that product's monograph. If it cannot resolve the product, it asks you — it never guesses.",
  "howTitle": "How it works",
  "how": {
    "resolve": {
      "title": "1. Resolve the medication",
      "body": "Your question can name a brand, an ingredient, or a DIN. The resolver maps it to exactly one product — and when two medication names look alike, a real cause of medication errors, it never auto-picks: it shows the candidates and you choose."
    },
    "scope": {
      "title": "2. Search only that monograph",
      "body": "We measured why this rule exists: a medication's name appears 33 times more often inside other drugs' monographs than inside its own. Searched corpus-wide, 8 of 40 test questions pulled passages from the wrong drug's documents; scoped to the resolved product, zero of 55 did. The corpus-wide path was deleted outright."
    },
    "route": {
      "title": "3. Route by intent",
      "body": "The question's intent — side effects, interactions, storage, and so on — steers the search toward the monograph sections where that kind of answer lives. Adding this routing raised the share of questions whose answer surfaces in the top five passages from 70% to 81% on our development set."
    },
    "guard": {
      "title": "4. Guard the result",
      "body": "Deterministic guards run before anything is phrased. Dosing questions are refused outright — a hard rule, not a preference. A brand that is not in the Canadian formulary gets a stated refusal, not a lookalike substitute. And an answer that would ship without sources becomes an honest 'I don't know' instead."
    }
  },
  "refusesTitle": "What it refuses to do",
  "refusesBody": "It will not answer dosing questions ('how much should I take' belongs to your pharmacist and your label). It will not recommend a therapy for a condition — product monographs describe products; they cannot rank treatments. And it will not silently substitute a similar-looking name for one it cannot find. Each refusal is worded as what it is, so you know why you did not get an answer.",
  "localNote": "This entire layer — resolver, search, and guards — runs deterministically on project hardware. No cloud service sees your question at this stage; the only cloud step is the Answer Voice that phrases the final answer from these retrieved, cited passages."
}
```

### FR

```json
"retrieval": {
  "breadcrumb": "Recherche dans les monographies",
  "heroLead": "Le quatrième des cinq cerveaux de MyPillSafe. Il {{desc}}",
  "whatTitle": "Ce qu'il fait",
  "whatBody1": "Quand vous posez une question, la Recherche dans les monographies trouve les passages qui y répondent — dans la monographie de produit officielle de Santé Canada de votre médicament, jamais sur l'internet ouvert. Derrière elle : un corpus de 6 803 monographies de produit, plus 27 documents d'ingrédients couvrant des produits courants en vente libre sans monographie propre, découpés en 3,9 millions de passages interrogeables.",
  "whatBody2": "Sa règle fondatrice : la recherche est <strong>limitée à un seul produit</strong>. Le système résout d'abord de quel produit vous parlez, puis ne cherche que dans la monographie de ce produit. S'il ne peut pas résoudre le produit, il vous le demande — il ne devine jamais.",
  "howTitle": "Comment il fonctionne",
  "how": {
    "resolve": {
      "title": "1. Résoudre le médicament",
      "body": "Votre question peut nommer une marque, un ingrédient ou un DIN. Le résolveur la rattache à exactement un produit — et quand deux noms de médicaments se ressemblent, une cause réelle d'erreurs de médication, il ne choisit jamais automatiquement : il affiche les candidats et c'est vous qui choisissez."
    },
    "scope": {
      "title": "2. Ne chercher que dans cette monographie",
      "body": "Nous avons mesuré pourquoi cette règle existe : le nom d'un médicament apparaît 33 fois plus souvent dans les monographies des autres médicaments que dans la sienne. En cherchant dans tout le corpus, 8 questions de test sur 40 ramenaient des passages des documents du mauvais médicament ; en limitant au produit résolu, zéro sur 55. Le chemin « tout le corpus » a été purement supprimé."
    },
    "route": {
      "title": "3. Orienter selon l'intention",
      "body": "L'intention de la question — effets secondaires, interactions, conservation, etc. — oriente la recherche vers les sections de la monographie où ce type de réponse se trouve. Cet aiguillage a fait passer la part des questions dont la réponse figure dans les cinq premiers passages de 70 % à 81 % sur notre ensemble de développement."
    },
    "guard": {
      "title": "4. Encadrer le résultat",
      "body": "Des garde-fous déterministes s'exécutent avant toute formulation. Les questions de posologie sont refusées d'emblée — une règle dure, pas une préférence. Une marque absente du répertoire canadien reçoit un refus explicite, pas un substitut au nom ressemblant. Et une réponse qui partirait sans sources devient un honnête « je ne sais pas »."
    }
  },
  "refusesTitle": "Ce qu'il refuse de faire",
  "refusesBody": "Il ne répond pas aux questions de posologie (« combien dois-je en prendre » relève de votre pharmacien et de votre étiquette). Il ne recommande pas de traitement pour une maladie — les monographies décrivent des produits ; elles ne peuvent pas classer des thérapies. Et il ne substitue jamais en silence un nom ressemblant à celui qu'il ne trouve pas. Chaque refus est formulé pour ce qu'il est, pour que vous sachiez pourquoi vous n'avez pas eu de réponse.",
  "localNote": "Toute cette couche — résolveur, recherche et garde-fous — s'exécute de façon déterministe sur le matériel du projet. Aucun service infonuagique ne voit votre question à cette étape ; la seule étape infonuagique est la Voix des réponses, qui formule la réponse finale à partir de ces passages récupérés et cités."
}
```

---

## §6 Answer Voice page — `public.brains.voice.*`

Sections: hero → what → the celecoxib story → how (3 steps) → measured cost + offline fallback →
back.

### EN

```json
"voice": {
  "breadcrumb": "Answer Voice",
  "heroLead": "The fifth of MyPillSafe's five brains. It is {{desc}}",
  "whatTitle": "What it does",
  "whatBody1": "The Answer Voice is the only part of MyPillSafe that runs in the cloud, and the only part allowed to write sentences for you. It receives the retrieved, cited monograph passages — already scoped and guarded by Monograph Retrieval — and phrases the answer in the language you chose. It is never asked to remember medicine on its own, and it decides nothing: what it says must come from the passages in front of it, and the citations are shown with the answer.",
  "whatBody2": "One sentence explains this whole design: <strong>the AI that talks is never the AI that decides.</strong>",
  "storyTitle": "The failure that shaped it",
  "storyBody": "During evaluation, a smaller language model was asked whether someone with a sulfa-drug allergy could take celecoxib. The passage it had itself retrieved and cited said allergic-type reactions had been demonstrated — and it still answered 'Yes, you can.' Every safety guard passed, because they checked which drug was cited, never whether the claim matched the source. That one answer settled the architecture: generation moved to a stronger cloud model, and a new deterministic check now compares each generated answer's safety-critical claims against the polarity of its own sources — on the cloud voice and the fallback alike.",
  "howTitle": "How it works",
  "how": {
    "receive": {
      "title": "1. Receive guarded context",
      "body": "The voice never searches. It receives the passages Monograph Retrieval already resolved, scoped, and guarded — with their citations — and the question. If the passages are missing, there is nothing to phrase, and it says so."
    },
    "phrase": {
      "title": "2. Phrase in your language",
      "body": "It writes the answer in the language you chose, in plain words, strictly from the supplied passages. Translation here is grounded in the official monograph text — never free-styled medical advice."
    },
    "recheck": {
      "title": "3. Get re-checked",
      "body": "The phrased answer passes back through deterministic guards, including the claim-source check born from the celecoxib failure. An answer that contradicts its own sources, or arrives without them, is replaced by an honest abstention with the same disclaimer every screen carries."
    }
  },
  "measuredTitle": "Measured, honestly",
  "measuredBody": "Answering our full 120-question evaluation set through the production voice cost $0.49 — about half a cent per answer. If the cloud model is unreachable, a local model answers instead and the app labels it as the offline fallback; the same guards run either way.",
  "measuredNote": "The evaluation set, per-question outcomes, and guard verdicts are part of the project's documentation and can be re-run."
}
```

### FR

```json
"voice": {
  "breadcrumb": "Voix des réponses",
  "heroLead": "Le cinquième des cinq cerveaux de MyPillSafe. C'est {{desc}}",
  "whatTitle": "Ce qu'elle fait",
  "whatBody1": "La Voix des réponses est la seule partie de MyPillSafe qui s'exécute dans le nuage, et la seule autorisée à écrire des phrases pour vous. Elle reçoit les passages de monographie récupérés et cités — déjà ciblés et encadrés par la Recherche dans les monographies — et formule la réponse dans la langue que vous avez choisie. On ne lui demande jamais de connaître la médecine par elle-même, et elle ne décide rien : ce qu'elle dit doit provenir des passages qui lui sont fournis, et les citations sont affichées avec la réponse.",
  "whatBody2": "Une phrase résume toute cette conception : <strong>l'IA qui parle n'est jamais l'IA qui décide.</strong>",
  "storyTitle": "L'échec qui l'a façonnée",
  "storyBody": "Pendant l'évaluation, on a demandé à un modèle de langage plus petit si une personne allergique aux sulfamides pouvait prendre du célécoxib. Le passage qu'il avait lui-même récupéré et cité indiquait que des réactions de type allergique avaient été démontrées — et il a quand même répondu « Oui, vous pouvez ». Tous les garde-fous étaient au vert, parce qu'ils vérifiaient quel médicament était cité, jamais si l'affirmation concordait avec la source. Cette seule réponse a tranché l'architecture : la génération est passée à un modèle infonuagique plus fort, et une nouvelle vérification déterministe compare désormais les affirmations critiques de chaque réponse générée à la polarité de ses propres sources — sur la voix infonuagique comme sur le mode de secours.",
  "howTitle": "Comment elle fonctionne",
  "how": {
    "receive": {
      "title": "1. Recevoir un contexte encadré",
      "body": "La voix ne cherche jamais. Elle reçoit les passages que la Recherche dans les monographies a déjà résolus, ciblés et encadrés — avec leurs citations — ainsi que la question. Si les passages manquent, il n'y a rien à formuler, et elle le dit."
    },
    "phrase": {
      "title": "2. Formuler dans votre langue",
      "body": "Elle rédige la réponse dans la langue que vous avez choisie, en mots simples, strictement à partir des passages fournis. La traduction s'ancre ici dans le texte officiel de la monographie — jamais un conseil médical improvisé."
    },
    "recheck": {
      "title": "3. Être revérifiée",
      "body": "La réponse formulée repasse par les garde-fous déterministes, dont la vérification affirmation-source née de l'échec du célécoxib. Une réponse qui contredit ses propres sources, ou qui arrive sans elles, est remplacée par une abstention honnête, avec le même avertissement que porte chaque écran."
    }
  },
  "measuredTitle": "Mesurée, honnêtement",
  "measuredBody": "Répondre à notre ensemble d'évaluation complet de 120 questions par la voix de production a coûté 0,49 $ — environ un demi-cent par réponse. Si le modèle infonuagique est injoignable, un modèle local répond à sa place et l'application l'étiquette comme mode de secours hors ligne ; les mêmes garde-fous s'exécutent dans les deux cas.",
  "measuredNote": "L'ensemble d'évaluation, les résultats question par question et les verdicts des garde-fous font partie de la documentation du projet et peuvent être réexécutés."
}
```

---

## §7 Help (signed-in) — tray mention

`en.json` → `help.trayNote` (rendered by `EducationPage` as a small muted note directly under
step s3):

```json
"trayNote": "In development: a wallet-size pill tray that holds up to six pills, imprint up, for a single photo. Until it ships, place one pill at a time on the capture card."
```

`fr.json` → `help.trayNote`:

```json
"trayNote": "En développement : un plateau à comprimés au format portefeuille qui accueille jusqu'à six comprimés, inscription vers le haut, pour une seule photo. D'ici là, placez un comprimé à la fois sur la carte de capture."
```

---

## §8 Claims the builder must NOT add

- No accuracy claim for the tray (NB08 has not run). The only tray numbers allowed are the ones in
  §3 (12/29 proxy, flash≈daylight), already framed as de-risk measurements.
- No "privacy: your profile is never sent to the cloud" claim on the voice page — it is plausible
  but unverified this session; the red team is checking `cb4_service.py`. If it verifies, the SA
  adds it later.
- No author names for MEDIC. No new citations beyond MEDIC.
- Never the words "100% accuracy" anywhere (standing rule from the rx page).

## §9 Complete file manifest (builder touches ONLY these)

| Path | Action |
|---|---|
| `dev/frontend/src/pages/public/brains/PillVisionPage.tsx` | create |
| `dev/frontend/src/pages/public/brains/DeterministicMatcherPage.tsx` | create |
| `dev/frontend/src/pages/public/brains/MonographRetrievalPage.tsx` | create |
| `dev/frontend/src/pages/public/brains/AnswerVoicePage.tsx` | create |
| `dev/frontend/src/assets/pillsafe-tray-render.jpg` | create (re-encoded from Brainstorm PNG) |
| `dev/frontend/src/content/fiveBrains.ts` | edit (4 hrefs + comment) |
| `dev/frontend/src/router/index.tsx` | edit (4 routes) |
| `dev/frontend/src/pages/public/SciencePage.tsx` | edit (MEDIC entry) |
| `dev/frontend/src/pages/dashboard/EducationPage.tsx` | edit (trayNote under s3) |
| `dev/frontend/src/i18n/locales/en.json` | edit (§1–§7 keys) |
| `dev/frontend/src/i18n/locales/fr.json` | edit (§1–§7 keys) |

Icons: builder's choice from lucide-react, consistent with existing pages (suggestions: vision —
Eye/Palette/Shapes/Type; matcher — Scale/Calculator/ShieldCheck; retrieval — BookOpen/Target/
Route/ShieldOff; voice — Cloud/Languages/RefreshCw).
