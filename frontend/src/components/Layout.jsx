import React, { useEffect, useState } from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import Logo from "../assets/jumpsol-logo.png"


const Layout = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [solBalance, setSolBalance] = useState(0);
    const [usdcBalance, setUsdcBalance] = useState(0);

    // Wallet Modal State
    const [showWalletModal, setShowWalletModal] = useState(false);
    const [modalWalletData, setModalWalletData] = useState({ address: 'Loading...', balances: [] });
    const [modalLoading, setModalLoading] = useState(false);

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const updateBalances = async () => {
        if (!user) return;
        try {
            const response = await axios.get('/api/wallet-balance');
            if (response.data.success) {
                let sol = 0;
                let usdc = 0;
                response.data.balances.forEach(b => {
                    if (b.token === 'SOL') sol = b.balance;
                    if (b.token === 'USDC') usdc = b.balance;
                });
                setSolBalance(sol);
                setUsdcBalance(usdc);
            }
        } catch (error) {
            console.error("Failed to update balances", error);
        }
    };

    useEffect(() => {
        if (user) {
            updateBalances();
            const interval = setInterval(updateBalances, 30000);
            return () => clearInterval(interval);
        }
    }, [user]);

    const openWalletModal = async (e) => {
        e.preventDefault();
        setShowWalletModal(true);
        fetchModalData();
    };

    const closeWalletModal = () => {
        setShowWalletModal(false);
    };

    const fetchModalData = async () => {
        setModalLoading(true);
        try {
            const infoRes = await axios.get('/api/wallet-info');
            const balanceRes = await axios.get('/api/wallet-balance');

            setModalWalletData({
                address: infoRes.data.success ? infoRes.data.wallet_address : 'Error',
                balances: balanceRes.data.success ? balanceRes.data.balances : []
            });
        } catch (error) {
            console.error("Error fetching modal data", error);
        } finally {
            setModalLoading(false);
        }
    };

    const copyModalAddress = () => {
        navigator.clipboard.writeText(modalWalletData.address);
    };

    return (
        <>
            {/* Navbar */}
            <nav className="navbar navbar-expand-lg fixed-top navbar-custom">
                <div className="container-xl">
                    <Link className="navbar-brand d-flex align-items-center gap-2" to="/dashboard">
                        <div className="logo d-flex align-items-center">
                            <img src={Logo} alt="AutoSOL" height={40} />
                        </div>
                    </Link>

                    {user && (
                        <>
                            <button className="navbar-toggler border-0" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                                <i className="fa-solid fa-bars text-muted"></i>
                            </button>

                            <div className="collapse navbar-collapse" id="navbarNav">
                                <div className="mx-auto"></div>

                                <div className="d-flex align-items-center gap-3">
                                    <div className="d-none d-lg-flex align-items-center px-3 py-1 rounded-pill gap-3"
                                        style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--glass-border)' }}>
                                        <div className="d-flex align-items-center gap-2">
                                            <span className="status-indicator status-active"></span>
                                            <span className="small font-archivo text-muted">MAINNET</span>
                                        </div>
                                        <div className="vr h-50 my-auto text-muted opacity-25"></div>
                                        <div className="d-flex align-items-center gap-2" title="SOL Balance">
                                            <i className="fa-brands fa-solana text-primary small"></i>
                                            <span className="small font-archivo text-light">{solBalance.toFixed(3)} SOL</span>
                                        </div>
                                        <div className="d-flex align-items-center gap-2" title="USDC Balance">
                                            <i className="fa-solid fa-dollar-sign text-success small"></i>
                                            <span className="small font-archivo text-light">{usdcBalance.toFixed(2)} USDC</span>
                                        </div>
                                    </div>

                                    <div className="dropdown">
                                        <button
                                            className="btn btn-sm btn-outline-secondary dropdown-toggle d-flex align-items-center gap-2 border-0"
                                            type="button" id="userDropdown" data-bs-toggle="dropdown">
                                            <i className="fa-solid fa-circle-user fa-lg text-primary"></i>
                                            <span>Account</span>
                                        </button>
                                        <ul className="dropdown-menu dropdown-menu-end shadow-lg"
                                            style={{ background: 'var(--bg-surface)', border: '1px solid var(--glass-border)' }}>
                                            <li>
                                                {/* Wallet Modal Trigger would go here, maybe passed as a prop or context? 
                                                    For now, let's keep it simple or implement a global modal context later.
                                                    OR just link to a dedicated wallet page if strictly adhering to React router patterns,
                                                    but the design uses a modal. I'll defer the modal implementation to the Dashboard page or a global one.
                                                 */}
                                                <a className="dropdown-item text-light" href="#" onClick={openWalletModal}>
                                                    <i className="fa-solid fa-wallet me-2 text-muted"></i>
                                                    Wallet
                                                </a>
                                            </li>
                                            <li>
                                                <hr className="dropdown-divider border-secondary" />
                                            </li>
                                            <li><button className="dropdown-item text-danger" onClick={handleLogout}><i
                                                className="fa-solid fa-right-from-bracket me-2"></i> Logout</button></li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </nav>

            {/* Main Content */}
            <main className="main-content">
                <Outlet />
            </main>

            {/* Wallet Modal */}
            {showWalletModal && (
                <>
                    <div className="modal fade show" style={{ display: 'block' }} tabIndex="-1" aria-modal="true" role="dialog">
                        <div className="modal-dialog modal-lg modal-dialog-centered">
                            <div className="modal-content glass-panel border-0 mb-0">
                                <div className="modal-header ">
                                    <h5 className="modal-title font-archivo">
                                        <i className="fa-solid fa-wallet text-primary me-2"></i>WALLET DETAILS
                                    </h5>
                                    <button type="button" className="btn-close" onClick={closeWalletModal} aria-label="Close"></button>
                                </div>
                                <div className="modal-body p-4">
                                    <div className="row">
                                        <div className="col-md-12">
                                            <div className="mb-4">
                                                <label className="form-label">Active Wallet Address</label>
                                                <div className="input-group">
                                                    <input type="text" className="form-control font-archivo" value={modalWalletData.address} readOnly
                                                        style={{ background: 'rgba(0,0,0,0.2)' }} />
                                                    <button className="btn btn-outline-secondary" type="button"
                                                        onClick={copyModalAddress} title="Copy Address">
                                                        <i className="fas fa-copy"></i>
                                                    </button>
                                                </div>
                                            </div>

                                            <div className="mb-4">
                                                <label className="form-label d-flex align-items-center gap-2">
                                                    <i className="fas fa-coins text-warning"></i>
                                                    Token Balances
                                                </label>
                                                <div className="table-responsive rounded border border-secondary border-opacity-25">
                                                    <table className="table table-hover mb-0">
                                                        <thead>
                                                            <tr>
                                                                <th>Token</th>
                                                                <th>Name</th>
                                                                <th className="text-end">Balance</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {modalLoading ? (
                                                                <tr>
                                                                    <td colSpan="3" className="text-center py-4 text-muted">
                                                                        <div className="spinner-border spinner-border-sm text-primary mb-2" role="status"></div>
                                                                        <div>Syncing chain data...</div>
                                                                    </td>
                                                                </tr>
                                                            ) : modalWalletData.balances.length > 0 ? (
                                                                modalWalletData.balances.map((b, idx) => (
                                                                    <tr key={idx}>
                                                                        <td>{b.token}</td>
                                                                        <td>{b.name || '-'}</td>
                                                                        <td className="text-end font-archivo">{b.balance.toFixed(6)}</td>
                                                                    </tr>
                                                                ))
                                                            ) : (
                                                                <tr><td colSpan="3" className="text-center text-muted">No assets found</td></tr>
                                                            )}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div className="modal-footer border-0 p-3">
                                    <button type="button" className="btn btn-primary" onClick={closeWalletModal}>Close</button>
                                    <button type="button" className="btn btn-primary" onClick={fetchModalData}>
                                        <i className="fas fa-sync-alt me-2"></i>Refresh Data
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="modal-backdrop fade show"></div>
                </>
            )}
        </>
    );
};

export default Layout;
