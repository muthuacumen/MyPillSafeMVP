# Phase 5 Content Pack — SA-authored copy (transcribe VERBATIM)

**Author:** /pillsafe SA · 2026-07-18
**Rule for the builder:** every sentence below was research-verified or deliberately written
qualitative. Transcribe verbatim into the pages. Do NOT add statistics, citations, percentages,
or capability claims that are not in this pack. Layout/styling is yours (PathoIntern-style);
words are not.

Citation verification log (SA, 2026-07-18 session): NLM Challenge (IEEE AIPR 2016, DOI
10.1109/AIPR.2016.8010584), MobileDeepPill (MobiSys 2017, DOI 10.1145/3081333.3081336),
Few-Shot Pill Recognition (CVPR 2020, DOI 10.1109/CVPR42600.2020.00981), CIHI Drug Use Among
Seniors in Canada (cihi.ca), ePillID (arXiv 2005.14288, verified 2026-07-01), GO-PILL (MDPI
Mathematics 2025, verified 2026-07-01), MedSnap (medRxiv 2020.05.06.20093427, verified
2026-07-15), Hanley & Lippman-Hand (JAMA 1983, PubMed 6827763, verified 2026-07-15).

---

## 1. Landing page (`/`) — "Introduction"

**Hero badge:** `Capstone MVP · Decision-Support Only`

**Headline:** The wrong pill should never go unnoticed.

**Sub-headline:** MyPillSafe is a medication-safety assistant for seniors and Canadians with
language barriers. It reads your prescription, verifies your pills from a photo, and answers
medication questions in your language — and when it isn't sure, it says so.

**CTA buttons:** `Get Started` → /register · `Learn More` → /about

### How MyPillSafe Works (4 step cards)

- **01 · Scan Your Prescription** — Photograph your prescription. MyPillSafe reads the
  medications and schedule and builds your personal medication profile.
- **02 · Confirm Your Medications** — Each medication is matched against Health Canada's
  Drug Identification Numbers (DINs). You confirm with one tap — MyPillSafe never guesses on
  your behalf.
- **03 · Verify a Pill** — Photograph a loose pill on the MyPillSafe capture card. Its colour,
  shape, and imprint are checked against *your* profile — not the whole formulary.
- **04 · Ask in Your Language** — Ask questions about your medications. Answers come only
  from Health Canada product monographs, with citations, in the language you choose.

### The Three-Outcome Safety Design (tier-card analog — MUST use the app's real decision colours)

Section intro line: *Every pill check ends in one of three honest outcomes. When MyPillSafe
isn't sure, abstaining is the design — not a failure.*

- **Verified** (green) — This pill matches a medication in your profile. You'll see exactly
  which attributes matched.
- **Needs a Closer Look** (amber) — MyPillSafe isn't sure yet. It may ask you to flip the pill
  and photograph the other side, or show you a short list to confirm.
- **Doesn't Match** (red) — This pill doesn't match anything in your profile. A clear warning,
  because a stray pill is exactly what MyPillSafe exists to catch.
- **Nothing Detected** (navy/neutral) — No pill found in the photo, with capture tips to try
  again.

Under-grid line: *MyPillSafe is tuned so that a wrong pill being called "verified" is the
rarest possible event — even at the cost of asking you to try again more often.*

### "Why not just identify any pill?" callout (small navy card between outcomes and science strip)

**Heading:** Why verify instead of identify?
**Body:** Because Canadian pills genuinely collide. In building our reference data we found
more than a dozen different products that are all the same "blue diamond tablet, SIL 25" —
cross-licensed generics no camera could ever tell apart. Against the whole formulary, that
problem is unsolvable; against the handful of medications *you* actually take, it is
tractable. That reframing — verify, don't identify — is the project's core idea.

### Scientific Foundation strip (4 cards, link to /about/science)

Intro: *MyPillSafe's design decisions rest on peer-reviewed evidence — including the evidence
that told us what NOT to build.*

1. **NLM Pill Image Recognition Challenge (2016)** — IEEE AIPR — Even the winning system
   found the right pill among its top five guesses only 43% of the time. Open-set pill
   identification is the wrong task for a safety app — so MyPillSafe verifies against your
   profile instead.
2. **ePillID (Usuyama et al., 2020)** — CVPR Workshops — The benchmark for fine-grained pill
   recognition with few examples per pill: most medications have almost no photos to learn
   from. MyPillSafe's attribute-based design avoids depending on per-pill image galleries.
3. **GO-PILL (2025)** — MDPI Mathematics — Reading the tiny imprint pressed into a pill is
   the hardest and most decisive step. MyPillSafe reads every imprint twice, with two
   complementary methods, before trusting it.
4. **CIHI — Drug Use Among Seniors in Canada** — 1 in 4 Canadian seniors is prescribed 10 or
   more drug classes, and seniors on 10+ medications are about five times more likely to be
   hospitalized for an adverse drug reaction.

### Closing CTA section

**Heading:** Built to warn, designed to abstain, never to guess.

**Body:** MyPillSafe is a capstone research project. It supports your decisions — it does not
make them. Every screen carries the same rule: verify with your pharmacist.

**Button:** `Read the Vision` → /about/vision

**Footer disclaimer (all public pages):** Decision-support only — not medical advice.
Always verify with a pharmacist or physician.

---

## 2. `/about` — About MyPillSafe

**Title:** About MyPillSafe
**Lede:** A medication-safety assistant built as five cooperating brains — each one doing the
job the evidence says it can actually do.

**Body (section: What MyPillSafe Is):**
MyPillSafe helps two groups the medication system underserves: seniors managing many
medications, and Canadians who read medical information more comfortably in a language other
than English or French. It turns a prescription into a personal medication profile, verifies
loose pills by photo against that profile, and answers medication questions from Health Canada
product monographs — with citations, in the user's language.

**Body (section: The Five Brains)** — render as 5 cards/rows:
- **Prescription Reader (OCR)** — reads the prescription image, extracts medications and
  schedule, and proposes Health Canada DIN matches that the user confirms — never auto-committed.
- **Pill Vision** — isolates the pill on the capture card and reads its colour (calibrated
  against the card's printed patches), shape, and imprint. The imprint is read twice by
  complementary methods.
- **Deterministic Matcher** — a transparent, formula-based scorer (deliberately not machine
  learning) that compares the pill's attributes against the user's confirmed medications and
  returns exactly one of: verify, abstain, or reject. Its thresholds are tuned to make false
  accepts the rarest event.
- **Monograph Retrieval** — finds the relevant, DIN-scoped passages of Health Canada product
  monographs, with deterministic safety guards — including a hard refusal to answer dosing
  questions.
- **Answer Voice (cloud AI)** — the only cloud component. It phrases the final answer in the
  user's language, strictly from the retrieved cited passages, and its answers are re-checked
  by the same deterministic guards.

**Body (section: Why this architecture):**
The split is deliberate: everything that decides is deterministic and auditable; the AI that
talks is never the AI that decides. That separation came from measurement, not taste — during
evaluation, a smaller language model answered a safety-critical allergy question incorrectly
*against its own retrieved source*. The architecture makes that class of failure detectable
and containable.

**Body (section: How we worked — render as 4 short bullets under its own heading):**
- **Measure the assumption before building on it.** The project's first reference dataset was
  rebuilt from scratch after a check revealed it described products that were approved in
  Canada but never actually sold — pills no patient could possess.
- **Pre-register the bar, then report honestly.** Every evaluation had its pass/fail criteria
  written down before the run. Some runs failed their gates; the failures are documented, not
  reframed.
- **Let the data decide.** Candidate models competed against simple zero-shot baselines — and
  on real phone photos, the baselines won two of three vision components. The trained models
  that looked better on studio benchmarks shipped only where they earned it.
- **Test everything.** A mandatory smoke test or spot-check ran on every build of the project
  — and every single one caught at least one real bug. The deterministic safety guards have a
  combined zero failures across all evaluation rounds; every incident came from the
  model-judgment layer, which is exactly why models don't make the decisions.

**Scope note:** MyPillSafe is a Conestoga College capstone project, built for Canada
(DIN-based, Health Canada monographs). It is decision-support only.

---

## 3. `/about/vision` — Vision & Mission

**Mission statement (hero):** To help seniors and Canadians with language barriers take the
right medication at the right time — by verifying what's in their hand, warning when something
is wrong, and explaining in the language they think in.

**Vision statement:** A Canada where a language barrier or a crowded pill organizer never
turns into a medication error — where every household has a safety layer that is honest about
what it knows and what it doesn't.

**Values (4 cards):**
- **Safety before convenience** — When evidence is thin, MyPillSafe abstains. An honest "I'm
  not sure — check with your pharmacist" beats a confident guess every time.
- **Evidence before features** — Every component earned its place through measurement.
  Features that failed evaluation were removed, not shipped.
- **Language is a safety feature** — Medication information you can't fully understand is a
  risk factor. Answering in the user's own language is core to the mission, not a nice-to-have.
- **Honesty about limits** — MyPillSafe is research-grade decision support with mandatory
  disclaimers, not a medical device. It says so on every screen.

---

## 4. `/about/problem` — Problem Statement

**Title:** The Problem
**Lede:** Polypharmacy is normal, pills look alike, and medication information assumes you
read English fluently.

**Stat cards (2, cited to CIHI):**
- **1 in 4** Canadian seniors is prescribed **10 or more** drug classes. *(CIHI, Drug Use
  Among Seniors in Canada)*
- **~5×** — seniors prescribed 10+ medications are about five times more likely to be
  hospitalized for an adverse drug reaction than seniors prescribed fewer. *(CIHI)*

**Body (section: The loose-pill moment):**
The riskiest moment in home medication use is mundane: a pill out of its bottle. In a weekly
organizer, on a counter, in a shared household — many tablets are small, white, and round,
and look-alike pairs are common. For a senior managing ten medications, "which pill is this?"
is a daily question with a non-trivial cost of getting it wrong.

**Body (section: Why "just identify the pill" fails):**
The obvious answer — an app that identifies any pill from a photo — has been tried at
research scale, and the results argue against it. In the U.S. National Library of Medicine's
Pill Image Recognition Challenge, the winning system placed the correct pill in its top five
candidates only 43% of the time on consumer photos. Against thousands of candidate products,
that is not a safety tool. MyPillSafe's reframing: don't identify against everything — verify
against the handful of medications *you actually take*, and refuse to guess beyond that.

**Body (section: The language barrier, stated without numbers):**
Many Canadians manage medications in a language they did not grow up with. Monographs,
labels, and pharmacy counselling largely assume English or French fluency. When
comprehension drops, adherence and safety drop with it. MyPillSafe treats translation into the
user's own language — grounded in the official monograph, never free-styled — as a
first-class safety function.

**Closing line:** MyPillSafe exists for the moment a hand hesitates over an open pill
organizer. Its job is to say "yes, that's yours", "no — stop", or "I'm not sure — check",
and to be trustworthy in all three.

---

## 5. `/about/science` — Scientific Foundation

**Title:** Scientific Foundation
**Lede:** Every design decision in MyPillSafe traces to published evidence or to our own
measured experiments — including the negative results.

### Section A — Published evidence MyPillSafe stands on (cards; each = citation + why it matters)

1. **Yaniv et al. — The NLM Pill Image Recognition Challenge (IEEE AIPR 2016)** — The
   founding evidence that open-set pill identification from consumer photos is unreliable:
   the challenge winner achieved only 43% top-5 accuracy. This is why MyPillSafe verifies
   against a personal profile instead of identifying against the full formulary.
2. **Zeng, Cao & Zhang — MobileDeepPill (ACM MobiSys 2017)** — The NLM challenge winner,
   showing pill recognition can run on a phone — and that colour, shape, and imprint each
   carry complementary signal, the same attribute decomposition MyPillSafe uses.
3. **Usuyama et al. — ePillID (CVPR Workshops 2020)** — Established the low-shot reality of
   pill recognition: most products have almost no training photos. MyPillSafe's text-attribute
   matching against Health Canada's registry avoids depending on per-pill image galleries.
4. **Ling et al. — Few-Shot Pill Recognition (CVPR 2020)** — Reinforces the few-shot framing
   with the CURE dataset and shows real-world capture conditions dominate difficulty —
   motivation for MyPillSafe's controlled capture card.
5. **GO-PILL (MDPI Mathematics 2025)** — Documents that low-contrast, debossed imprints are
   the hardest OCR case in pill imaging. Our own evaluation independently confirmed the
   imprint is the decisive, hardest attribute — MyPillSafe reads it twice with complementary
   methods and never trusts a single read.
6. **MedSnap ID (medRxiv 2020; related US patents)** — Prior commercial art pairing a capture
   tray with a phone pill app — for medication *authentication* (counterfeit detection), not
   patient-profile verification. MyPillSafe cites it as prior art; our open, ablated capture-card
   design and verification-with-rejection task are the differences.
7. **Hanley & Lippman-Hand (JAMA 1983)** — "If nothing goes wrong, is everything all right?"
   The rule of three: how we size our safety evaluations, so "no false accepts observed" comes
   with an honest statistical upper bound instead of a marketing claim.
8. **CIHI — Drug Use Among Seniors in Canada** — The population evidence behind the problem
   statement: 1 in 4 Canadian seniors on 10+ drug classes; ~5× adverse-drug-reaction
   hospitalization risk at 10+ medications.

### Section B — Our own research (in preparation) — MUST render with an "In Preparation" badge

**Working title:** *Verify, Don't Identify: Profile-Constrained Pill Verification from
Consumer Photos with a Printed Capture Card.*

**One-paragraph description:**
MyPillSafe's pill-vision pipeline is itself a research contribution in preparation. The paper
formalizes verification-with-rejection against a patient's own medication profile as the
right task for consumer pill safety; introduces a printed capture card that turns an
uncontrolled phone photo into a calibrated one (white-balance patches, known geometry,
forced flash); contributes a harmonized, human-adjudicated appearance reference for over
7,000 marketed Canadian DINs; and reports the negative results that shaped the system — most
notably that on real phone photos, zero-shot models beat our fine-tuned ones on two of three
vision heads, a caution for anyone trusting studio benchmarks.

**Honest status block (verbatim, keep the pending-work sentence):**
*Status: in preparation. The design-phase experiments are complete; a pre-registered
confirmatory capture study (the "tray v2" campaign — a pilot shoot followed by a 600-photo
protocol with defined usability and safety endpoints) is still pending, and the paper will
be drafted from those results. Until then, MyPillSafe's measured performance figures remain
development-set diagnostics, and we deliberately do not quote them as product claims.*

### Section C — Design principles the evidence forced (3 short cards)

- **Verify, don't identify** — the NLM challenge's 43% is the argument in one number.
- **The AI that talks is never the AI that decides** — deterministic matching and guards
  decide; the language model only phrases, strictly from cited sources, and is re-checked.
  Measurement forced this: a medication's name appears many times more often in *other*
  drugs' documents than in its own, so only deterministic scoping — not clever ranking —
  reliably prevents wrong-drug answers.
- **Abstention is a feature** — the system is tuned so a false "verified" is the rarest
  event, at the accepted cost of more "I'm not sure" outcomes.

---

## 6. `/about/team` — Team

**Title:** The Team
**Lede:** A five-person capstone team at Conestoga College.

- **Muthuraj Jayakumar** — Project Lead · ML Architecture
- **Sumanth Reddy** — Backend & Systems Integration
- **Lohith Reddy** — Frontend & User Experience
- **Ali Ozdemir** — Data Engineering · Reference Pipeline
- **Abdullah Mohammed** — Quality Assurance & Evaluation

**Note under grid:** MyPillSafe is a capstone project of the Conestoga College graduate program
in AI & Machine Learning.

---

## 7. About-chain order (AboutNav prev/next, PathoIntern pattern)

Home → `/about` (About) → `/about/vision` (Vision & Mission) → `/about/problem` (Problem
Statement) → `/about/science` (Scientific Foundation) → `/about/team` (Team) → last "next"
CTA = `Get Started` → /register. Contact page stays, linked from footer, outside the chain.

---

## 8. Assistant widget strings

- **Name:** MyPillSafe Assistant
- **Header badge:** `Project Guide · No Medical Advice`
- **Header subline:** About this project · Not a medication tool
- **Disclaimer strip:** ⚠️ This assistant explains the MyPillSafe project only. It cannot
  answer questions about your medications — use "Ask about my medication" in the app, and
  always verify with a pharmacist.
- **Greeting (EN):** Hello! I'm the MyPillSafe Assistant. I can explain how MyPillSafe works —
  the pill verification, the safety design, the research behind it, and the team. I can't
  answer questions about your medications; the app has a dedicated, safeguarded Q&A for
  that. What would you like to know?
- **Greeting (FR):** Bonjour ! Je suis l'Assistant MyPillSafe. Je peux vous expliquer comment
  MyPillSafe fonctionne — la vérification des comprimés, la conception axée sur la sécurité,
  la recherche et l'équipe. Je ne peux pas répondre aux questions sur vos médicaments ;
  l'application dispose d'une section Q&R dédiée et sécurisée pour cela. Que voulez-vous
  savoir ?
- **Medication-redirect reply (EN):** That sounds like a question about a medication. I'm
  only the project guide — for medication questions, please use **Ask about my medication**
  inside the app (it answers from official Health Canada monographs, with citations), and
  always confirm with your pharmacist. *(+ button linking to /dashboard/qa when logged in,
  /login otherwise)*
- **Medication-redirect reply (FR):** Cela ressemble à une question sur un médicament. Je ne
  suis que le guide du projet — pour les questions sur les médicaments, utilisez **Poser une
  question sur mon médicament** dans l'application (réponses tirées des monographies
  officielles de Santé Canada, avec citations), et confirmez toujours avec votre pharmacien.
- **Out-of-scope fallback (EN):** I'm not sure that's something I know — I can answer
  questions about the MyPillSafe project: how it works, its safety design, the research, and
  the team. Try one of the suggestions below.
- **Out-of-scope fallback (FR):** Je ne suis pas certain de pouvoir répondre à cela — je peux
  répondre aux questions sur le projet MyPillSafe : son fonctionnement, sa conception axée sur
  la sécurité, la recherche et l'équipe. Essayez l'une des suggestions ci-dessous.
- **Clarification prompt (EN):** I found a few related topics — which one did you mean?
- **Clarification prompt (FR):** J'ai trouvé quelques sujets connexes — lequel vouliez-vous
  dire ?

**CB4 system-prompt requirements (builder implements, SA intent binding):** answer ONLY from
the provided knowledge-base context; explainer scope only; NEVER answer medication-specific
questions (drug names, doses, interactions, side effects, "can I take") — always redirect per
the strings above; answer in the requested language (en/fr); ≤180 words per answer; no
statistics or citations beyond those present in the KB context; friendly-plain tone; always
truthful that MyPillSafe is a capstone and decision-support only.
