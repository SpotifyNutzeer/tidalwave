import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import TopList from './TopList.svelte';

describe('TopList', () => {
  it('renders the title and ranked rows', () => {
    render(TopList, { props: { title: 'Top Artists', items: [
      { label: 'Daft Punk', count: 10 },
      { label: 'Kavinsky', count: 4 }
    ] } });
    expect(screen.getByRole('heading', { name: 'Top Artists' })).toBeInTheDocument();
    expect(screen.getByText('Daft Punk')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('renders an empty hint when there are no items', () => {
    render(TopList, { props: { title: 'Top Artists', items: [] } });
    expect(screen.getByText(/no data/i)).toBeInTheDocument();
  });
});
