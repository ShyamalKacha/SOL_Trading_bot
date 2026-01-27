
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

const History = () => {
    // State
    const [orders, setOrders] = useState([]);
    const [network, setNetwork] = useState('mainnet');
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [loading, setLoading] = useState(false);

    // Optional: Keep date filter if user wants specific day, but "same as order log" implies general history
    // For now, mirroring Order Log exactly as requested, but keeping Network filter

    useEffect(() => {
        fetchOrders(1);
    }, [network]); // Refetch when network changes

    const fetchOrders = async (page = 1) => {
        setLoading(true);
        // Clear old data while loading to show feedback
        setOrders([]);
        try {
            const response = await axios.get(`/api/orders?page=${page}&per_page=15&network=${network}`);
            if (response.data.success) {
                setOrders(response.data.orders);
                setTotalPages(response.data.pagination.total_pages);
                setCurrentPage(page);
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
            <div className="glass-panel mb-4">
                <div className="glass-body py-3">
                    <div className="row align-items-center">
                        <div className="col-md-4">
                            <label className="form-label mb-0 me-2">Network Filter:</label>
                            <select
                                className="form-select font-archivo d-inline-block w-auto"
                                value={network}
                                onChange={(e) => setNetwork(e.target.value)}
                            >
                                <option value="mainnet">Mainnet</option>
                                <option value="devnet">Devnet</option>
                                <option value="testnet">Testnet</option>
                            </select>
                        </div>
                        <div className="col-md-8 text-end">
                            <button className="btn btn-sm btn-outline-secondary" onClick={() => fetchOrders(currentPage)} disabled={loading}>
                                <i className={`fas fa-sync-alt me-1 ${loading ? 'fa-spin' : ''}`}></i> Refresh
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Results */}
            <div className="glass-panel">
                <div className="glass-header d-flex justify-content-between align-items-center">
                    <div className="d-flex align-items-center gap-2">
                        <i className="fa-solid fa-list-ul text-white"></i>
                        <h5 className="font-archivo tracking-tight mb-0">EXECUTION LOG</h5>
                    </div>
                </div>
                <div className="glass-body p-0">
                    {/* PC View - Table */}
                    <div className="table-responsive d-none d-md-block">
                        <table className="table table-hover mb-0">
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>Network</th>
                                    <th>Action</th>
                                    <th>Amount</th>
                                    <th>Asset</th>
                                    <th>Exec Price</th>
                                    <th>P&L</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading ? (
                                    <tr><td colSpan="8" className="text-center py-5 font-archivo">Loading history...</td></tr>
                                ) : orders && orders.length > 0 ? (
                                    orders.map((tx, idx) => (
                                        <tr key={idx}>
                                            <td>{new Date(tx.timestamp).toLocaleString()}</td>
                                            <td><span className={`badge ${tx.network === 'mainnet' ? 'bg-primary' : 'bg-warning text-dark'}`}>{tx.network}</span></td>
                                            <td><span className={`badge ${tx.action === 'buy' ? 'bg-success' : 'bg-danger'}`}>{tx.action.toUpperCase()}</span></td>
                                            <td>{tx.amount ? `$${tx.amount.toFixed(2)}` : '-'}</td>
                                            <td>{tx.token_symbol}</td>
                                            <td>${typeof tx.price === 'number' ? tx.price.toFixed(4) : tx.price}</td>
                                            <td className={tx.pnl >= 0 ? 'text-success' : 'text-danger'}>
                                                {tx.pnl !== null ? (tx.pnl >= 0 ? '+' : '') + '$' + Math.abs(tx.pnl).toFixed(4) : '-'}
                                            </td>
                                            <td><span className="badge bg-secondary">{tx.status ? tx.status.toUpperCase() : 'COMPLETED'}</span></td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan="8" className="text-center py-5 text-muted font-archivo">
                                            NO TRADES FOUND
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Mobile View - Cards */}
                    <div className="d-md-none p-3">
                        {loading ? (
                            <div className="text-center py-5 font-archivo">Loading history...</div>
                        ) : orders && orders.length > 0 ? (
                            orders.map((tx, idx) => (
                                <div key={idx} className="glass-panel mb-3 p-3" style={{ background: 'rgba(255,255,255,0.03)' }}>
                                    <div className="d-flex justify-content-between align-items-center mb-2">
                                        <span className="text-muted small">{new Date(tx.timestamp).toLocaleString()}</span>
                                        <span className={`badge ${tx.network === 'mainnet' ? 'bg-primary' : 'bg-warning text-dark'}`}>{tx.network}</span>
                                    </div>
                                    <div className="d-flex justify-content-between align-items-center mb-2">
                                        <div className="d-flex align-items-center gap-2">
                                            <span className={`badge ${tx.action === 'buy' ? 'bg-success' : 'bg-danger'}`}>{tx.action.toUpperCase()}</span>
                                            <span className="fw-bold">{tx.token_symbol}</span>
                                        </div>
                                        <div className={tx.pnl >= 0 ? 'text-success fw-bold' : 'text-danger fw-bold'}>
                                            {tx.pnl !== null ? (tx.pnl >= 0 ? '+' : '') + '$' + Math.abs(tx.pnl).toFixed(4) : '-'}
                                        </div>
                                    </div>
                                    <div className="d-flex justify-content-between small text-muted">
                                        <span>Amt: {tx.amount ? `$${tx.amount.toFixed(2)}` : '-'}</span>
                                        <span>Price: ${typeof tx.price === 'number' ? tx.price.toFixed(4) : tx.price}</span>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="text-center py-5 text-muted">NO TRADES FOUND</div>
                        )}
                    </div>

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                        <div className="p-3 border-top border-secondary border-opacity-10 d-flex justify-content-between align-items-center">
                            <button className="btn btn-sm btn-outline-secondary"
                                onClick={() => fetchOrders(currentPage - 1)} disabled={currentPage === 1 || loading}>
                                <i className="fas fa-chevron-left me-1"></i> Prev
                            </button>
                            <span className="font-archivo small text-muted">Page {currentPage} of {totalPages}</span>
                            <button className="btn btn-sm btn-outline-secondary"
                                onClick={() => fetchOrders(currentPage + 1)} disabled={currentPage === totalPages || loading}>
                                Next <i className="fas fa-chevron-right ms-1"></i>
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default History;
