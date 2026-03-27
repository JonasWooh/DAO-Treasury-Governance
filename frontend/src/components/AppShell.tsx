import { NavLink, Outlet } from 'react-router-dom';

import type { RuntimeBundle } from '../types';

const NAV_ITEMS = [
  { to: '/', label: 'Overview' },
  { to: '/proposals', label: 'Pipeline' },
  { to: '/submit', label: 'Submit' },
  { to: '/treasury', label: 'Treasury' },
  { to: '/evidence', label: 'Evidence' },
];

interface AppShellProps {
  bundle: RuntimeBundle;
  runtimeNote?: string;
}

export function AppShell({ bundle, runtimeNote }: AppShellProps) {
  const activeMembers = bundle.fundingState.members.filter((member) => member.isActive).length;
  const activeProjects = bundle.fundingState.projects.length;
  const proposalCount = bundle.fundingState.proposals.length;

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero-grid">
          <div className="hero-copy">
            <span className="eyebrow">Campus Innovation Fund</span>
            <h1>Campus Innovation Fund DAO</h1>
            <p>
              A capital allocation workspace for funding review, milestone approvals, and treasury
              oversight on Sepolia.
            </p>
            <div className="hero-tag-row" aria-label="Platform capabilities">
              <span className="hero-tag">Hybrid voting</span>
              <span className="hero-tag">Milestone releases</span>
              <span className="hero-tag">Treasury controls</span>
            </div>
          </div>
          <aside className="hero-aside" aria-label="Portfolio summary">
            <article className="hero-stat">
              <span className="hero-stat-label">Active members</span>
              <strong className="hero-stat-value">{activeMembers}</strong>
            </article>
            <article className="hero-stat">
              <span className="hero-stat-label">Funding requests</span>
              <strong className="hero-stat-value">{proposalCount}</strong>
            </article>
            <article className="hero-stat">
              <span className="hero-stat-label">Live projects</span>
              <strong className="hero-stat-value">{activeProjects}</strong>
            </article>
          </aside>
        </div>
      </header>
      {runtimeNote ? (
        <section className="runtime-banner">
          <div className="runtime-banner-card">
            <span className="status status-warning">Preview mode</span>
            <p className="muted runtime-banner-copy">{runtimeNote}</p>
          </div>
        </section>
      ) : null}
      <nav className="top-nav" aria-label="Primary">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => (isActive ? 'nav-link nav-link-active' : 'nav-link')}
            end={item.to === '/'}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="page-frame">
        <Outlet />
      </main>
    </div>
  );
}
