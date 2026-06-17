import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import RecentList from './RecentList.svelte';

describe('RecentList', () => {
  it('renders each recent track with its artist', () => {
    render(RecentList, { props: { items: [
      { track: 'Nightcall', artist: 'Kavinsky', album: 'OutRun', played_at: '2024-06-17T12:00:00Z' }
    ] } });
    expect(screen.getByText('Nightcall')).toBeInTheDocument();
    expect(screen.getByText('Kavinsky')).toBeInTheDocument();
  });
});
