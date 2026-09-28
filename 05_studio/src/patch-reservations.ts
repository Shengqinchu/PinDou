import { contentModule } from './content-store';
import defaults from './content/patch-reservations.json';
export const patchCopy = contentModule('patch-reservations', defaults);
export type ExperienceFilter = 'all' | 'beads' | 'patch';
export const bookingExperience = (plan: string) => plan === 'patch' ? 'patch' : 'beads';
