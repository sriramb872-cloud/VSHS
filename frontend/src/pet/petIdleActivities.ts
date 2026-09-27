/**
 * Idle companion lines. The key must be `text` - `PetWidget` reads
 * `content.text` for every state (greeting/notify/happy/... and idle), so these
 * previously used `caption` and rendered an empty speech bubble in the idle
 * state.
 */
export interface PetSpeech {
  emoji: string;
  text: string;
}

export const idleActivities: PetSpeech[] = [
  { emoji: '📖', text: 'reading quietly...' },
  { emoji: '🧮', text: 'remembering 7 × 8...' },
  { emoji: '🔤', text: 'recalling a spelling word...' },
  { emoji: '🙆', text: 'stretching...' },
];
