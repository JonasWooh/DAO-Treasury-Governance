import { groupScreenshots, flattenEvidenceTransactions } from '../lib/evidence';
import { formatAddress, toEtherscanAddressLink } from '../lib/formatters';
import type { RuntimeBundle } from '../types';

interface EvidencePageProps {
  bundle: RuntimeBundle;
}

export function EvidencePage({ bundle }: EvidencePageProps) {
  const transactionRows = flattenEvidenceTransactions(bundle.evidence, bundle.config.etherscanBaseUrl);
  const screenshotsBySection = groupScreenshots(bundle.screenshots.screenshots);

  return (
    <div className="page-grid single-column">
      <section className="panel panel-wide">
        <h2>Operational Record</h2>
        <p className="muted">
          Review the published artifacts behind this workspace, including contract addresses,
          execution history, funding state, and archived media.
        </p>
      </section>

      <section className="panel panel-wide">
        <h3>Network Snapshot</h3>
        <div className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">Members</span>
            <strong className="metric-value">{bundle.fundingState.members.length}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Proposals</span>
            <strong className="metric-value">{bundle.fundingState.proposals.length}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Projects</span>
            <strong className="metric-value">{bundle.fundingState.projects.length}</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Total Active Reputation</span>
            <strong className="metric-value">{bundle.fundingState.reputationSummary.totalActiveReputation}</strong>
          </div>
        </div>
      </section>

      <section className="panel panel-wide">
        <h3>Member Standing</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Account</th>
              <th>Registered</th>
              <th>Active</th>
              <th>Current Reputation</th>
            </tr>
          </thead>
          <tbody>
            {bundle.fundingState.members.map((member) => (
              <tr key={member.account}>
                <td>
                  <a
                    className="quick-link quick-link-code"
                    href={toEtherscanAddressLink(bundle.config.etherscanBaseUrl, member.account)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <code>{formatAddress(member.account)}</code>
                  </a>
                </td>
                <td>{member.isRegistered ? 'yes' : 'no'}</td>
                <td>{member.isActive ? 'yes' : 'no'}</td>
                <td>{member.currentReputation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel panel-wide">
        <h3>Contract Registry</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Address</th>
              <th>Etherscan</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(bundle.deployments.contracts).map(([name, address]) => (
              <tr key={name}>
                <td>{name}</td>
                <td>
                  <a
                    className="quick-link quick-link-code"
                    href={toEtherscanAddressLink(bundle.config.etherscanBaseUrl, address)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <code>{formatAddress(address)}</code>
                  </a>
                </td>
                <td>
                  <a href={toEtherscanAddressLink(bundle.config.etherscanBaseUrl, address)} target="_blank" rel="noreferrer">
                    Open
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel panel-wide">
        <h3>Execution Log</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Section</th>
              <th>Step</th>
              <th>Transaction Hash</th>
              <th>Etherscan</th>
            </tr>
          </thead>
          <tbody>
            {transactionRows.map((row) => (
              <tr key={`${row.section}-${row.step}-${row.txHash}`}>
                <td>{row.section}</td>
                <td>{row.step}</td>
                <td>
                  <a className="quick-link quick-link-code" href={row.url} target="_blank" rel="noreferrer">
                    <code>{formatAddress(row.txHash)}</code>
                  </a>
                </td>
                <td>
                  <a href={row.url} target="_blank" rel="noreferrer">
                    Open
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel panel-wide">
        <h3>Media Checklist</h3>
        <div className="stack">
          {Object.entries(screenshotsBySection).map(([section, entries]) => (
            <div key={section}>
              <h4>{section}</h4>
              <ul className="mono-list compact-list">
                {entries.map((entry) => (
                  <li key={entry.id}>
                    <span>{entry.caption}</span>
                    <code>{entry.expectedPath}</code>
                    <span className={entry.required ? 'status status-error' : 'status status-good'}>
                      {entry.required ? 'required' : 'optional'}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
