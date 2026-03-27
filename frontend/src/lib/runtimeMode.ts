import type { RuntimeBundle } from '../types';

export function isPreviewRuntime(bundle: RuntimeBundle): boolean {
  const note = bundle.config.note?.toLowerCase() ?? '';
  return note.includes('preview data is active');
}
