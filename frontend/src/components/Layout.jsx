import React, { useEffect, useState } from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import Logo from "../assets/jumpsol-logo.png"

import { useWallet } from '../context/WalletContext';

const Layout = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    // USE WALLET CONTEXT - NO MORE API CALLS HERE!
    const {
        walletAddress,
        balances,
        selectedNetwork,
        solBalance,
        usdcBalance,
        loading: walletLoading,
        changeNetwork,
        refreshWalletData
    } = useWallet();

    // Wallet Modal State
    const [showWalletModal, setShowWalletModal] = useState(false);

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    const openWalletModal = (e) => {
        e.preventDefault();
        setShowWalletModal(true);
        // Data is already available from context - no need to fetch!
    };

    const closeWalletModal = () => {
        setShowWalletModal(false);
    };

    const copyModalAddress = () => {
        navigator.clipboard.writeText(walletAddress);
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
                            <div className="d-flex align-items-center gap-2 gap-md-3 ms-auto">
                                <div className="d-flex align-items-center px-3 py-1 rounded-pill gap-3"
                                    style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--glass-border)' }}>

                                    {/* NETWORK DROPDOWN */}
                                    <div className="dropdown">
                                        <button className="btn btn-sm btn-link text-light text-decoration-none p-0 d-flex align-items-center gap-2 dropdown-toggle"
                                            type="button" id="networkDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                                            <span className={`status-indicator ${selectedNetwork === 'mainnet' ? 'status-active' : selectedNetwork === 'devnet' ? 'status-warning' : 'status-inactive'}`}></span>
                                            <span className="small font-archivo text-main fw-bold">{selectedNetwork.toUpperCase()}</span>
                                        </button>
                                        <ul className="dropdown-menu dropdown-menu-end shadow-lg"
                                            style={{ background: 'var(--bg-surface)', border: '1px solid var(--glass-border)' }}>
                                            <li>
                                                <button className={`dropdown-item text-light ${selectedNetwork === 'mainnet' ? 'active' : ''}`}
                                                    onClick={() => changeNetwork('mainnet')}>
                                                    <i className="fa-solid fa-circle text-success me-2"></i>Mainnet (Live)
                                                </button>
                                            </li>
                                            <li>
                                                <button className={`dropdown-item text-light ${selectedNetwork === 'devnet' ? 'active' : ''}`}
                                                    onClick={() => changeNetwork('devnet')}>
                                                    <i className="fa-solid fa-circle text-warning me-2"></i>Devnet (Test)
                                                </button>
                                            </li>
                                            <li>
                                                <button className={`dropdown-item text-light ${selectedNetwork === 'testnet' ? 'active' : ''}`}
                                                    onClick={() => changeNetwork('testnet')}>
                                                    <i className="fa-solid fa-circle text-info me-2"></i>Testnet (Beta)
                                                </button>
                                            </li>
                                        </ul>
                                    </div>

                                    <div className="vr h-50 my-auto text-muted opacity-25"></div>
                                    <div className="d-flex align-items-center gap-2" title="SOL Balance">
                                        <i className="fa-brands fa-solana text-primary small"></i>
                                        <span className="small font-archivo text-light">{solBalance.toFixed(4)}<span className="d-none d-md-inline"> SOL</span></span>
                                    </div>
                                    <div className="d-flex align-items-center gap-2" title="USDC Balance">
                                        <i className="fa-solid fa-dollar-sign text-success small"></i>
                                        <span className="small font-archivo text-light">{usdcBalance.toFixed(4)}<span className="d-none d-md-inline"> USDC</span></span>
                                    </div>
                                </div>

                                <button className="navbar-toggler border-0" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                                    <i className="fa-solid fa-bars text-muted"></i>
                                </button>
                            </div>

                            <div className="collapse navbar-collapse" id="navbarNav">
                                <div className="mx-auto"></div>

                                <div className="d-flex align-items-center gap-3">
                                    <div className="dropdown">
                                        <button
                                            className="btn btn-sm btn-outline-secondary dropdown-toggle d-flex align-items-center gap-2 border-0"
                                            type="button" id="userDropdown" data-bs-toggle="dropdown">
                                            <i className="fa-solid fa-circle-user fa-lg text-primary"></i>
                                            <span className="d-lg-inline d-none">Account</span>
                                        </button>
                                        <ul className="dropdown-menu dropdown-menu-end shadow-lg"
                                            style={{ background: 'var(--bg-surface)', border: '1px solid var(--glass-border)' }}>
                                            <li>
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
                                <div className="modal-header">
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
                                                    <input type="text" className="form-control font-archivo" value={walletAddress} readOnly
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
                                                            {walletLoading ? (
                                                                <tr>
                                                                    <td colSpan="3" className="text-center py-4 text-muted">
                                                                        <div className="spinner-border spinner-border-sm text-primary mb-2" role="status"></div>
                                                                        <div>Syncing chain data...</div>
                                                                    </td>
                                                                </tr>
                                                            ) : balances.length > 0 ? (
                                                                balances.map((b, idx) => (
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
                                    <button type="button" className="btn btn-primary" onClick={refreshWalletData}>
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
