import {
  AtomIcon,
  BookIcon,
  LeafIcon,
  SigmaIcon,
  StarIcon,
} from '../components/ui/icons.jsx'

export const SUBJECTS = {
  Matematika: { color: 'var(--subj-math)', Icon: SigmaIcon },
  Mathematics: { color: 'var(--subj-math)', Icon: SigmaIcon },
  Math: { color: 'var(--subj-math)', Icon: SigmaIcon },
  Biologi: { color: 'var(--subj-bio)', Icon: LeafIcon },
  Biology: { color: 'var(--subj-bio)', Icon: LeafIcon },
  Fisika: { color: 'var(--subj-physics)', Icon: AtomIcon },
  Physics: { color: 'var(--subj-physics)', Icon: AtomIcon },
  Kimia: { color: 'var(--subj-physics)', Icon: AtomIcon },
  Chemistry: { color: 'var(--subj-physics)', Icon: AtomIcon },
  'Bahasa Inggris': { color: 'var(--subj-english)', Icon: BookIcon },
  English: { color: 'var(--subj-english)', Icon: BookIcon },
}

export const SUBJECT_NAMES = Object.keys(SUBJECTS)

export function getSubjectConfig(subject) {
  return SUBJECTS[subject] || { color: 'var(--mm)', Icon: StarIcon }
}
