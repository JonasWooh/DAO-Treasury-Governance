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
        <h2>Evidence</h2>
        <p className="muted">
          The evidence package is driven by the Sepolia deployment manifest, proposal scenario
          manifest, demo evidence manifest, and screenshot manifest. Missing entries are treated as
          build or validation failures rather than silently omitted.
        </p>
      </section>

      <section className="panel panel-wide">
        <h3>Contract Links</h3>
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
                <td><code>{formatAddress(address)}</code></td>
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
        <h3>Transaction Hash Table</h3>
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
                <td><code>{formatAddress(row.txHash)}</code></td>
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
        <h3>Screenshot Manifest</h3>
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
