import { useEffect, useMemo, useState } from 'react';
import type { BillingTenantHealth } from '@/types';
import { fetchBillingUsage } from '@/utils/apiClient';

interface SummaryMetrics {
  averageHealth: number;
  atRiskTenants: number;
  watchlist: number;
  totalSeats: number;
}

function computeSummary(tenants: BillingTenantHealth[]): SummaryMetrics {
  if (!tenants.length) {
    return { averageHealth: 0, atRiskTenants: 0, watchlist: 0, totalSeats: 0 };
  }
  const aggregate = tenants.reduce(
    (acc, tenant) => {
      acc.averageHealth += tenant.health_score;
      if (tenant.health_score < 0.75 || tenant.usage_ratio > 0.95) {
        acc.atRiskTenants += 1;
      }
      if (tenant.usage_ratio > 0.85) {
        acc.watchlist += 1;
      }
      acc.totalSeats += tenant.seats_requested || 0;
      return acc;
    },
    { averageHealth: 0, atRiskTenants: 0, watchlist: 0, totalSeats: 0 }
  );
  return {
    averageHealth: aggregate.averageHealth / tenants.length,
    atRiskTenants: aggregate.atRiskTenants,
    watchlist: aggregate.watchlist,
    totalSeats: aggregate.totalSeats,
  };
}

export function CustomerHealthDashboard(): JSX.Element {
  const [token, setToken] = useState('');
  const [tenants, setTenants] = useState<BillingTenantHealth[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const stored = window.localStorage.getItem('cocounsel.billingToken');
    if (stored) {
      setToken(stored);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    if (token) {
      window.localStorage.setItem('cocounsel.billingToken', token);
    } else {
      window.localStorage.removeItem('cocounsel.billingToken');
    }
  }, [token]);

  const refresh = async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetchBillingUsage(token || undefined);
      const sorted = [...response.tenants].sort((a, b) => a.health_score - b.health_score);
      setTenants(sorted);
      setLastUpdated(response.generated_at);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to load customer health metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const summary = useMemo(() => computeSummary(tenants), [tenants]);

  return (
    <div className="health-dashboard">
      <header className="health-header">
        <div>
          <h2>Customer Health</h2>
          <p>
            Monitor quota burn, support posture, and commercial risk across every tenant. Provide a bearer token with
            <code>billing:read</code> scope to hydrate the dashboard.
          </p>
        </div>
        <div className="token-entry">
          <label>
            Billing bearer token
            <input
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              placeholder="Paste OAuth token"
            />
          </label>
          <button type="button" onClick={() => void refresh()} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </header>

      {error && (
        <div role="alert" className="health-error">
          {error}
        </div>
      )}

      <section className="health-summary" aria-live="polite">
        <article>
          <h3>Average health</h3>
          <p>{summary.averageHealth ? `${Math.round(summary.averageHealth * 100)}%` : 'n/a'}</p>
        </article>
        <article>
          <h3>At-risk tenants</h3>
          <p>{summary.atRiskTenants}</p>
        </article>
        <article>
          <h3>Watchlist</h3>
          <p>{summary.watchlist}</p>
        </article>
        <article>
          <h3>Committed seats</h3>
          <p>{summary.totalSeats}</p>
        </article>
      </section>

      <section className="health-table-wrapper">
        <div className="health-table-header">
          <h3>Tenant health ledger</h3>
          {lastUpdated && <span>Updated {new Date(lastUpdated).toLocaleString()}</span>}
        </div>
        <div className="health-table-scroll">
          <table className="health-table">
            <thead>
              <tr>
                <th scope="col">Tenant</th>
                <th scope="col">Plan</th>
                <th scope="col">Health</th>
                <th scope="col">Usage</th>
                <th scope="col">Success rate</th>
                <th scope="col">Seats</th>
                <th scope="col">Projected cost</th>
                <th scope="col">Last activity</th>
              </tr>
            </thead>
            <tbody>
              {tenants.length === 0 ? (
                <tr>
                  <td colSpan={8} className="empty-state">
                    {loading ? 'Loading telemetry…' : 'No telemetry recorded yet.'}
                  </td>
                </tr>
              ) : (
                tenants.map((tenant) => (
                  <tr key={tenant.tenant_id} data-health={tenant.health_score < 0.75 ? 'at-risk' : 'healthy'}>
                    <th scope="row">
                      <div className="tenant-cell">
                        <span className="tenant-id">{tenant.tenant_id}</span>
                        <span className="tenant-support">{tenant.support_tier}</span>
                      </div>
                    </th>
                    <td>{tenant.plan_label}</td>
                    <td>{Math.round(tenant.health_score * 100)}%</td>
                    <td>{(tenant.usage_ratio * 100).toFixed(1)}%</td>
                    <td>{Math.round(tenant.success_rate * 100)}%</td>
                    <td>{tenant.seats_requested || 0}</td>
                    <td>${tenant.projected_monthly_cost.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                    <td>{new Date(tenant.last_event_at).toLocaleString()}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
