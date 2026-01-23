import React, { useState } from 'react';
import axios from 'axios';
import { toast, ToastContainer } from 'react-toastify';

const History = () => {
    const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
    const [loading, setLoading] = useState(false);
    const [historyData, setHistoryData] = useState(null);

    const fetchHistory = async () => {
        if (!date) {
            toast.warning("Please select a date");
            return;
        }

        setLoading(true);
        setHistoryData(null);

        try {
            const response = await axios.post('/api/trades/history', { date });
            if (response.data.success) {
                setHistoryData(response.data);
                if (response.data.count === 0) {
                    toast.info("No trades found for this date", { theme: "dark" });
                }
            } else {
                toast.error(response.data.message || "Failed to fetch history");
            }
        } catch (error) {
            console.error("History fetch error", error);
            toast.error("Error fetching trade history");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container-xl pb-5">
            <ToastContainer position="bottom-right" theme="dark" />

            {/* Header */}
            <div className="row align-items-end mb-4">
                <div className="col-md-8">
                    <h6 className="text-primary tracking-wide text-uppercase mb-2"><i className="fas fa-history me-2"></i>Archive</h6>
                    <h1 className="display-5 fw-bold mb-0">TRADE <span className="text-primary-gradient">HISTORY</span></h1>
                    <p className="text-muted mt-2 mb-0">Historical performance analysis and trade logs.</p>
                </div>
            </div>

            {/* Filter Panel */}
            <div className="glass-panel">
                <div className="glass-header">
                    <div className="d-flex align-items-center gap-2">
                        <i className="fa-solid fa-filter text-info"></i>
                        <h5 className="font-mono tracking-tight">SEARCH FILTERS</h5>
                    </div>
                </div>
                <div className="glass-body">
                    <div className="row align-items-end g-3">
                        <div className="col-md-4">
                            <label className="form-label">Select Date</label>
                            <input
                                type="date"
                                className="form-control font-mono"
                                value={date}
                                onChange={(e) => setDate(e.target.value)}
                            />
                        </div>
                        <div className="col-md-2">
                            <button className="btn btn-primary w-100 font-mono" onClick={fetchHistory} disabled={loading}>
                                {loading ? <span className="spinner-border spinner-border-sm me-2"></span> : <i className="fas fa-search me-2"></i>}
                                LOAD
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Results */}
            {historyData && (
                <div className="glass-panel">
                    <div className="glass-header d-flex justify-content-between align-items-center">
                        <div className="d-flex align-items-center gap-2">
                            <i className="fa-solid fa-list-ul text-white"></i>
                            <h5 className="font-mono tracking-tight mb-0">EXECUTION LOG</h5>
                        </div>
                        <div className={`badge font-mono ${historyData.total_pnl >= 0 ? 'bg-success' : 'bg-danger'}`}>
                            Daily P&L: {historyData.total_pnl >= 0 ? '+' : ''}{historyData.total_pnl.toFixed(4)}
                        </div>
                    </div>
                    <div className="glass-body p-0">
                        <div className="table-responsive">
                            <table className="table table-hover mb-0">
                                <thead>
                                    <tr>
                                        <th>Timestamp</th>
                                        <th>Action</th>
                                        <th>Token</th>
                                        <th className="text-end">Price</th>
                                        <th className="text-end">Amount</th>
                                        <th className="text-end">P&L</th>
                                        <th className="text-center">Status</th>
                                    </tr>
                                </thead>
                                <tbody className="font-mono">
                                    {historyData.trades.length > 0 ? (
                                        historyData.trades.map((trade, idx) => (
                                            <tr key={idx}>
                                                <td>{trade.timestamp}</td>
                                                <td>
                                                    <span className={`badge ${trade.action === 'buy' ? 'bg-success' : 'bg-danger'}`}>
                                                        {trade.action.toUpperCase()}
                                                    </span>
                                                </td>
                                                <td>{trade.token_symbol}</td>
                                                <td className="text-end">${trade.price.toFixed(4)}</td>
                                                <td className="text-end">{trade.amount.toFixed(4)}</td>
                                                <td className={`text-end ${trade.pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                                                    {trade.pnl ? (trade.pnl >= 0 ? '+' : '') + trade.pnl.toFixed(4) : '-'}
                                                </td>
                                                <td className="text-center">
                                                    {trade.status === 'confirmed' ? (
                                                        <i className="fas fa-check-circle text-success" title="Confirmed"></i>
                                                    ) : (
                                                        <i className="fas fa-clock text-warning" title="Pending"></i>
                                                    )}
                                                </td>
                                            </tr>
                                        ))
                                    ) : (
                                        <tr>
                                            <td colSpan="7" className="text-center py-5 text-muted">
                                                No trading activity recorded for this date.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default History;
