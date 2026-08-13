// The five of us, in one place.
//
// PEOPLE'S NAMES AND INITIALS ARE NOT TRANSLATED — they are the same string
// in every locale, so they live in code, not in en.json/fr.json. That rule
// predates this file (it was written at the top of TeamPage.tsx); what is new
// is that the names now live in code EXACTLY ONCE.
//
// WHY THAT MATTERS: a name used to be duplicated across TeamPage.tsx,
// footer.credits in en.json, and footer.credits in fr.json — three copies
// with no link between them. A misspelling ("Abdullah Mohammed" for
// "Abdallah Mohamed") got into one and propagated to seven files across the
// repo before anyone caught it. One array is the fix.
//
// Roles and responsibility bullets ARE language and stay in
// `public.team.members.*` in both locale files, keyed by `key` below.

export interface TeamMember {
  /** i18n key suffix for this member's role/responsibility copy. */
  key: string;
  initials: string;
  name: string;
  /** Tailwind class for the avatar tile — brand palette, not semantic. */
  avatarBg: string;
  linkedin: string;
}

export const TEAM: readonly TeamMember[] = [
  {
    key: 'mj',
    initials: 'MJ',
    name: 'Muthuraj Jayakumar',
    avatarBg: 'bg-navy',
    linkedin: 'https://www.linkedin.com/in/mu2j/',
  },
  {
    key: 'sr',
    initials: 'SR',
    name: 'Sumanth Reddy',
    avatarBg: 'bg-teal-600',
    linkedin: 'https://www.linkedin.com/in/sumanth-reddy-konannagari/',
  },
  {
    key: 'lr',
    initials: 'LR',
    name: 'Lohith Reddy',
    avatarBg: 'bg-burnt',
    linkedin: 'https://www.linkedin.com/in/lohith-reddy-danda-618403344/',
  },
  {
    key: 'ao',
    initials: 'AO',
    name: 'Ali Ozdemir',
    avatarBg: 'bg-coral',
    linkedin: 'https://www.linkedin.com/in/itsalicihan/',
  },
  {
    key: 'am',
    initials: 'AM',
    name: 'Abdallah Mohamed',
    avatarBg: 'bg-navy',
    linkedin: 'https://www.linkedin.com/in/abdalla-awahab/',
  },
] as const;
