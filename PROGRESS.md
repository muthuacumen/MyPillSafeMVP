# PillSafe — Progress Report (Plain-English Version)

**Last updated:** 2026-07-06

This document explains the PillSafe project in everyday language. You do not need to know anything about computers, coding, or technology to read it. If you want the technical version (for developers), see `README.md` instead — this document is for explaining the project to anyone, including someone with zero technical background.

---

## 1. What is PillSafe, in one sentence?

PillSafe is a phone/computer app that helps people figure out **what medicine they are holding and whether it is safe to take**, by taking a photo of it with a camera.

---

## 2. What problem does it solve?

Imagine an elderly person who has six different pill bottles on their kitchen counter. The labels are printed in tiny text. Sometimes pills fall out of their bottles and get mixed up. Sometimes a caregiver isn't sure if they already gave a dose this morning. Mistakes like this genuinely send people to the hospital every year.

PillSafe is built to prevent that, by:
- Reading a prescription label automatically from a photo, so nobody has to squint at tiny print.
- Remembering what medicine someone is supposed to take and when.
- Letting someone photograph a loose, unlabeled pill and checking whether it matches anything they're actually supposed to be taking.
- Speaking everything out loud, for anyone who has trouble seeing or reading.

PillSafe **never replaces a doctor or pharmacist** — it is a safety-net tool, not medical advice. The app says this clearly to every user.

---

## 3. Who is this app for?

- **Elderly patients** who manage several medications at once.
- **Caregivers** (family members, home-care workers) helping someone else manage medication.
- **People with low vision** — everything can be read aloud instead of read on screen.
- **Anyone** who finds prescription labels confusing.

---

## 4. How does someone actually use it? (step by step)

1. **Sign up** for a free account, like signing up for any website (just an email and a password).
2. **Take a photo** of a prescription label using the camera built into the app — no typing required.
3. The app **reads the label automatically**. If the photo is of a prescription letter listing several medications at once (common with pharmacy printouts), it now correctly splits them into separate entries instead of mashing them into one — each with its own medicine name, dose, and exact clock time(s) to take it (not just a vague "morning/afternoon/evening" guess).
4. The home screen shows a **"next dose" countdown** and a **simple daily schedule** in time order — what to take and when, colour-coded by time of day. Medicines that are "take as needed" (like a painkiller) are shown differently, with the safe daily maximum, instead of being forced into a fake fixed schedule.
5. If someone finds a **loose pill** and isn't sure what it is, they can photograph it. The app looks at its colour and shape and tries to match it against a known list of medications.
6. If the pill **matches** something the person is supposed to be taking, the app shows a green "all good" message. If it **doesn't match anything**, the app shows a clear red warning telling them not to take it without checking with a pharmacist.
7. A **speaker icon** lets anyone turn on a voice that reads the screen, the schedule, and the results out loud.
8. Before showing any result, a **reminder pop-up** repeats that this is not medical advice and to always check with a pharmacist or doctor.

---

## 5. What has been built and works today

Think of the app as having two halves: the part people see and tap on (the "front of house"), and the part working behind the scenes that stores information and does the thinking (the "back of house", like a kitchen behind a restaurant counter). Both halves are built and working.

### Account & daily use
- ✅ Sign up, log in, log out — works like any normal app.
- ✅ A home screen showing a personal daily medicine schedule.
- ✅ A profile page where someone can update their name, phone number, language, and password, or permanently delete their account if they want to.
- ✅ A settings page to turn notifications on/off, turn the voice assistant on/off, and choose a language.

### Scanning medicine
- ✅ **Fixed a real bug reported by a user:** prescription photos were not being read at all — a setting that switches on the real label-reading software had accidentally been left off, so every photo, no matter what medicine was actually in it, silently produced the same fixed placeholder answer instead. This was found, fixed, and re-tested end-to-end against a real multi-medication photo to confirm it now correctly reads whatever is actually in the picture. This setting is now switched on by default, both for everyday use and for when the app is put online for others to use.
- ✅ Pointing the camera at a prescription label, taking a photo, and having the app automatically read it. **One photo can now contain several medications** (a typical pharmacy printout listing 2-3 prescriptions at once) — the app correctly separates them into individual entries instead of merging everything into one garbled record, and no longer mistakes the clinic's letterhead name for a medicine. If the camera isn't available or permission is denied, it lets someone upload a photo instead.
- ✅ For each medicine found, the app now works out the **dose** (e.g. "200mg"), the **exact times to take it** (e.g. 8:00 AM, 1:00 PM, and 6:00 PM — not just a vague "three times a day"), whether it should be **taken with food**, and — for "take as needed" medicines like a painkiller — the **safe maximum amount per day**.
- ✅ A "My Medications" page listing everything currently being tracked, with colour-coded tags showing morning / afternoon / evening / night (or a distinct "as needed" tag with its daily limit).
- ✅ Anyone can **look at the original photo of their prescription again**, right from their medication list — useful for double-checking against what the app read.
- ✅ A **"Read my instructions" panel** on every medication card shows a full, plain-language sentence of exactly how and when to take it (dose, time, food, reason) — and it can be read in **English, French, Arabic, or Spanish**, in extra-large text designed for easier reading.
- ✅ A "Hear Reminder" button on every medication card that speaks a short, friendly reminder out loud — in the patient's choice of **English, French, Arabic, or Spanish** — so someone who reads better in one of those languages than in English still gets a clear spoken reminder.
- ✅ **Automatic reminders while the app is open**: the app now pops up a notification and speaks a reminder 30 minutes before each scheduled dose, and again right at the dose time — without anyone having to ask for it. (This only works while the app is open in a browser tab — it does not yet send notifications when the app/browser is fully closed; see "What's not finished yet.")
- ✅ The home screen highlights the **single next dose coming up** with a live countdown, above a full chronological list of everything scheduled for the rest of the day.
- ✅ A "loose pill checker" — take a photo of an unlabeled pill, and the app works out its colour and shape using real image analysis (not guesswork), then checks it against a reference list.
- ✅ A safety check that compares what was scanned against what the person is actually supposed to be taking, and shows a clear green / amber / red result.

### Safety & trust features
- ✅ A reminder pop-up shown the very first time anyone uses the app, and again before every scan result — it cannot be skipped or clicked away from accidentally, only dismissed by reading and pressing "I Understand."
- ✅ A "Safety Records" page showing a history of every past scan and whether it matched.
- ✅ A "Medication Education" page with plain-language explanations of how to use the app, how to read a prescription label, what the app can and can't do, general medication safety tips, and a list of frequently asked questions.
- ✅ A voice assistant (a speaker icon) that reads page names, the daily schedule, and scan results out loud for anyone who prefers listening over reading.

### Public pages (no account needed)
- ✅ A welcome/home page explaining what PillSafe is, for people who haven't signed up yet.
- ✅ An "About" page explaining the mission, who it's for, and the team behind it.
- ✅ A "Contact" page with a simple form to send a message to the team.

### Behind the scenes (administration & safety)
- ✅ A separate area for the people who run/manage the app (administrators), used for things like seeing how many people are using the app. Administrators are **technically blocked** from ever seeing an individual patient's private medication or scan history — this isn't just a promise in writing, the system itself refuses the request if an administrator's account ever tries.
- ✅ Every piece of personal medication information is locked to the one person who owns it — nobody else's account can ever see it.
- ✅ A safety-style double-check system: the project has 40 automated tests that run every time a change is made, automatically checking that none of the safety rules above have been accidentally broken. All 40 currently pass.

### The look and feel
- ✅ A clean, light-colored design (no hard-to-read dark backgrounds), with larger text and big, easy-to-tap buttons, aimed at being comfortable for elderly users and accessible for people with low vision.
- ✅ The **welcome/home page, sign-in, sign-up, dashboard, and profile pages were redesigned** to feel more polished and trustworthy: a clearer welcome page explaining how the app works and who it's for, a nicer-looking sign-in/sign-up experience (with a visual password-strength indicator and a "show password" toggle), a dashboard that greets people differently depending on the time of day, and a profile page that's organized into clear, labeled sections instead of one long list.
- ✅ Friendlier handling when something goes wrong or there's nothing to show yet — instead of a blank screen or an endless spinner, people now see a clear, honest message (e.g. "no scans yet" or "something went wrong, tap to try again") in the places that previously had none.
- ✅ The "Forgot password?" link — which previously did nothing at all when clicked — now honestly tells the person that password reset isn't available yet and to contact support, instead of silently failing to do anything.
- ✅ Pages now load faster one at a time instead of all at once (so someone visiting just the home page doesn't have to download the entire app first), which matters more as more people use the app at the same time.
- ✅ The two top-bar icons noted previously as slightly too small to tap easily (voice assistant, notifications) have been resized to the recommended 44-pixel easy-tap size.

---

## 6. What's not finished yet (being fully honest)

- **The "loose pill checker" can describe a pill's colour and shape, but can't yet name it.** It needs to be checked against an official Canadian government medicine reference list (which includes things like "this colour + this shape + this text stamped on it = Tylenol 500mg"). That official list has **not been loaded into the app yet** — nobody had access to the real data file during this round of work. Think of it like a dictionary with all the pages and structure in place, but no words written in yet. The "lookup system" works; it just has nothing to look up against right now.
- **A more advanced AI writer (from a company called Anthropic, the makers of "Claude") is fully wired up and ready to write friendly, plain-language explanations of scan results** — but it's switched off until someone adds a paid access key (a bit like a subscription password) to the app's settings. Without it, the app still works, it just won't show that extra AI-written explanation.
- **The automatic label-reading tool ("OCR") was found to be silently switched off, producing a bug where every prescription photo returned the same placeholder medicine — this has now been fixed** (see "Scanning medicine" above) and is switched on by default. The automated tests still pass with it on, so there's no longer a reason to leave it off.
- **Reminders only work while the app is open in a browser tab.** The 30-minutes-before and at-time alerts described above do not yet fire if the browser/app is fully closed — that would need a separate "push notification" system (similar to how some apps notify you even when closed), which was deliberately left for a future round given the time available.
- **The medication-instruction sentences are built from the extracted dose/time/food information, not a live AI translation of the photo's exact wording.** This keeps the French/Arabic/Spanish text reliable and free, but it means the wording is a clear plain-language summary rather than a word-for-word translation of what the doctor originally typed.
- **Some of the newer pages are only available in English.** Older parts of the app (login, sign-up, the main dashboard, admin pages) are available in both English and French; the newest pages and sections built in this round (the redesigned welcome page, and new dashboard/profile sections like Safety Alerts and Caregiver info) haven't been translated to French yet.
- **The app hasn't been visually tested on a tablet-sized screen specifically**, though the design is built to automatically resize for different screen sizes.

None of the above stop the app from working — they're either deliberate decisions (waiting on real data, waiting on a paid key) or small polish items for later.

---

## 7. A few simple definitions, if you want them

- **"Front end"** — the part of the app you actually see and tap on: the screens, the buttons, the camera view.
- **"Back end"** — the part working behind the scenes that you never see directly: it stores information and does the actual thinking, like a kitchen behind a restaurant counter.
- **"Database"** — where the app permanently remembers information, like a digital filing cabinet. PillSafe currently uses a simple, lightweight one called SQLite that doesn't need any extra setup.
- **"API"** — the way the front end and back end talk to each other, like a waiter carrying an order from your table to the kitchen and bringing food back.
- **"OCR"** — software that reads printed or handwritten text out of a photograph, turning a picture of words into actual computer text.
- **"AI guidance"** — a written explanation generated by an artificial intelligence model, in this case to describe a pill in plain language.
- **"Automated tests"** — small scripted checks that run by themselves and confirm the important safety rules (like "a patient's data can never be seen by anyone else") are still true every time the code changes.

---

## 8. How to see it for yourself

If you'd like to actually look at the app running:
1. Ask whoever manages the project's code to "start the backend and frontend servers" (this just means switching the app on).
2. Once it's running, open a web browser and go to the address they give you (normally something like `http://localhost:5173` on the same computer).
3. From there you can click around just like any website — sign up for an account, look at the dashboard, try the camera scanning, etc.

For the technical setup steps, see `README.md`.

---

## 9. Where things stand right now — quick snapshot

| Area | Status |
|---|---|
| Sign up / log in / accounts | Fully working |
| Daily medicine schedule, with "next dose" countdown | Fully working |
| Scanning a prescription label, including multiple medicines on one photo | Fully working (a bug that silently returned a placeholder medicine for every photo has been fixed; real label-reading is switched on by default and tested against a real multi-medication letter) |
| Dose, exact times, food timing, and "as needed" max-dose extraction | Fully working |
| Viewing the original prescription photo again later | Fully working |
| My Medications list | Fully working |
| Plain-language, multilingual "Read my instructions" panel | Fully working (English / French / Arabic / Spanish) |
| Automatic 30-minutes-before + at-time reminders | Fully working while the app is open; does not yet work when the app is fully closed |
| Loose pill photo checker (colour & shape) | Fully working |
| Matching a scanned pill against your medicine list | Fully working |
| Official medicine name lookup | Built, but the reference list is empty — pending real data |
| AI-written plain-language descriptions | Built, switched off until a paid access key is added |
| Safety reminders & warnings | Fully working |
| Voice assistant (read aloud) | Fully working |
| Profile, Settings, Safety history, Education pages | Fully working |
| Public Home / About / Contact pages | Fully working |
| Administrator area, with patient-privacy lockout | Fully working |
| Automated safety checks (tests) | 40 out of 40 passing |
| Multilingual voice reminders (English / French / Arabic / Spanish) | Fully working |
| Look and feel (light theme, large text, big buttons) | Done — home, sign-in/sign-up, dashboard, and profile pages redesigned this round; one minor exception remains (French translation gap on the newest sections, noted above) |

---

*PillSafe · Conestoga College Graduate AI/ML Program · AIML-6900 Capstone*
