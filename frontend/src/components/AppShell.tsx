import { NavLink, Outlet } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/', label: 'Overview' },
  { to: '/proposals', label: 'Proposals' },
  { to: '/treasury', label: 'Treasury & NAV' },
  { to: '/evidence', label: 'Evidence' },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero-copy">
          <span className="eyebrow">Industrial-Quality DAO Prototype on Sepolia</span>
          <h1>Campus Innovation Fund DAO</h1>
          <p>
            A governance-first treasury demo that shows delegated voting, timelocked execution,
            constrained grant release, Aave idle-fund management, and Chainlink-backed NAV
            reporting.
          </p>
        </div>
      </header>
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
