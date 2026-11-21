import React, { useState, useEffect } from 'react';
import { auditApi } from '../../api/audit';
import { extractApiError, formatUtcTimestamp } from '../../utils/format';
import { ShieldCheck, Filter, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [entityFilter, setEntityFilter] = useState('');
  const [userIdFilter, setUserIdFilter] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 50;
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    loadLogs();
  }, [actionFilter, entityFilter, userIdFilter, page]);

  const loadLogs = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const params = {
        skip: page * pageSize,
        limit: pageSize,
      };
      if (actionFilter.trim()) params.action = actionFilter.trim();
      if (entityFilter.trim()) params.entity_name = entityFilter.trim();
      if (userIdFilter.trim()) {
        const uid = parseInt(userIdFilter.trim(), 10);
        if (!isNaN(uid)) params.user_id = uid;
      }
      const data = await auditApi.getAuditLogs(params);
      setLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      setErrorMsg(extractApiError(err, 'Failed to load audit logs.'));
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearFilters = () => {
    setActionFilter('');
    setEntityFilter('');
    setUserIdFilter('');
    setPage(0);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Institutional Audit Trail</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Immutable, append-only transaction logs for marks, attendance, and account claims (R-014, D-013).
          </p>
        </div>
        <button
          onClick={loadLogs}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh Trail
        </button>
      </div>

      {errorMsg && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-xs text-rose-800 rounded-lg">
          {errorMsg}
        </div>
      )}

      {/* Filter Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-3.5 shadow-sm flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
          <Filter className="w-3.5 h-3.5" /> Filter by:
        </div>
        <input
          type="text"
          placeholder="Action (e.g. mark.updated)"
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="px-2.5 py-1 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <input
          type="text"
          placeholder="Entity (e.g. mark, student)"
          value={entityFilter}
          onChange={(e) => setEntityFilter(e.target.value)}
          className="px-2.5 py-1 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <input
          type="number"
          placeholder="User ID (e.g. 1)"
          value={userIdFilter}
          onChange={(e) => setUserIdFilter(e.target.value)}
          className="w-28 px-2.5 py-1 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
        />
        {(actionFilter || entityFilter || userIdFilter) && (
          <button
            onClick={handleClearFilters}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 text-slate-500 text-left">
              <tr>
                <th className="py-2.5 px-3 font-semibold">Timestamp</th>
                <th className="py-2.5 px-3 font-semibold">User ID</th>
                <th className="py-2.5 px-3 font-semibold">Action</th>
                <th className="py-2.5 px-3 font-semibold">Target Entity</th>
                <th className="py-2.5 px-3 font-semibold">Values (Old &rarr; New)</th>
                <th className="py-2.5 px-3 font-semibold">Audit Justification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">
                    {loading ? 'Loading audit trail...' : 'No audit records match the selected filters.'}
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/60">
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                      {formatUtcTimestamp(log.timestamp || log.created_at)}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-600">
                      {log.user_id ? `User #${log.user_id}` : 'System'}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="font-semibold text-indigo-700 font-mono text-[11px]">
                        {log.action}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-medium capitalize">
                      {log.entity_name} {log.entity_id ? `#${log.entity_id}` : ''}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] max-w-xs truncate">
                      {log.old_values ? (
                        <span className="text-slate-400 line-through mr-1">
                          {JSON.stringify(log.old_values)}
                        </span>
                      ) : null}
                      <span className="text-emerald-700 font-semibold">
                        {JSON.stringify(log.new_values)}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-slate-600 text-xs italic">
                      {log.reason || 'Routine operation'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Bounded Pagination Controls */}
        <div className="p-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <div>
            Showing {logs.length} entries (Page {page + 1})
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || loading}
              className="inline-flex items-center gap-1 px-3 py-1 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed font-medium text-slate-700"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Previous
            </button>
            <span className="font-semibold text-slate-700 px-1">
              Page {page + 1}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={logs.length < pageSize || loading}
              className="inline-flex items-center gap-1 px-3 py-1 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed font-medium text-slate-700"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
