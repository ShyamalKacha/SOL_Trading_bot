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
    // Drawer State (for mobile)
    const [showDrawer, setShowDrawer] = useState(false);

    const handleLogout = async () => {
        await logout();
        setShowDrawer(false);
        navigate('/login');
    };

    const openWalletModal = (e) => {
        e.preventDefault();
        setShowWalletModal(true);
        setShowDrawer(false); // Close drawer when opening wallet modal
    };

    const closeWalletModal = () => {
        setShowWalletModal(false);
    };

    const copyModalAddress = () => {
        navigator.clipboard.writeText(walletAddress);
    };

    const toggleDrawer = () => {
        setShowDrawer(!showDrawer);
    };

    const handleNetworkChange = (network) => {
        changeNetwork(network);
        setShowDrawer(false);
    };

    // Close drawer when clicking outside
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (showDrawer && !e.target.closest('.mobile-drawer') && !e.target.closest('.navbar-toggler')) {
                setShowDrawer(false);
            }
        };

        if (showDrawer) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [showDrawer]);

    return (
        <>
            {/* Navbar */}
            <nav className="navbar navbar-expand-lg fixed-top navbar-custom">
                <div className="container-xl">
                    <Link className="navbar-brand d-flex align-items-center gap-2" to="/dashboard">
                        <div className="d-flex align-items-center">
                            {/* Mobile */}
                            <img
                                src={Logo}
                                alt="AutoSOL"
                                height={28}
                                className="d-block d-sm-none"
                            />

                            {/* Tablet + Desktop */}
                            <img
                                src={Logo}
                                alt="AutoSOL"
                                height={35}
                                className="d-none d-sm-block"
                            />
                        </div>
                    </Link>

                    {user && (
                        <>
                            <div className="d-flex align-items-center gap-2 gap-md-3 ms-auto">
                                {/* Desktop Network Dropdown & Balances - Hidden on mobile */}
                                <div className="d-none d-lg-flex align-items-center rounded-pill gap-1">
                                    {/* NETWORK DROPDOWN */}
                                    <div className="dropdown fixed-pill" 
                                         style={{ background: '#C1FF72', border: '1px solid var(--glass-border)' }}>
                                        <button className="btn btn-sm btn-link text-black text-decoration-none p-0 d-flex align-items-center gap-1 dropdown-toggle"
                                            type="button" id="networkDropdown" data-bs-toggle="dropdown" aria-expanded="false">
                                            <span className={`status-indicator`}></span>
                                            <span className="small font-archivo text-black fw-bold">{selectedNetwork.toUpperCase()}</span>
                                        </button>
                                        <ul className="dropdown-menu dropdown-menu-end shadow-lg">
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

                                    <div className="fixed-pill d-flex gap-2"  style={{ background: '#C1FF72', border: '1px solid var(--glass-border)' }}>
                                        <div className="d-flex align-items-center gap-2" title="SOL Balance">
                                            <span className="small font-archivo text-black fw-bold">{solBalance.toFixed(4)}<span className=""> SOL</span></span>
                                        </div>
                                        <div className="d-flex align-items-center gap-2" title="USDC Balance">
                                            <span className="small font-archivo text-black fw-bold">{usdcBalance.toFixed(4)}<span className=""> USDC</span></span>
                                        </div>
                                    </div>
                                </div>

                                {/* Mobile: Show balances only */}
                                <div className="d-flex d-lg-none align-items-center gap-1">
                                    <div className="fixed-pill d-flex gap-2"  style={{ background: '#C1FF72', border: '1px solid var(--glass-border)' }}>
                                        <div className="d-flex align-items-center gap-1" title="SOL Balance">
                                            <span className="small font-archivo text-black fw-bold">{solBalance.toFixed(2)}<span className=""> SOL</span></span>
                                        </div>
                                        <div className="d-flex align-items-center gap-1" title="USDC Balance">
                                            <span className="small font-archivo text-black fw-bold">{usdcBalance.toFixed(2)}<span className=""> USDC</span></span>
                                        </div>
                                    </div>
                                </div>

                                {/* Burger Menu - Visible on mobile/tablet */}
                                <button 
                                    className="navbar-toggler border-0 d-lg-none" 
                                    type="button" 
                                    onClick={toggleDrawer}
                                    aria-label="Toggle navigation"
                                >
                                    <i className={`fa-solid ${showDrawer ? 'fa-times' : 'fa-bars'} text-muted`}></i>
                                </button>
                            </div>

                            {/* Desktop Menu - Hidden on mobile/tablet */}
                            <div className="d-none d-lg-flex align-items-center gap-3 ms-3">
                                <div className="dropdown">
                                    <button
                                        className="btn btn-sm btn-outline-secondary dropdown-toggle d-flex align-items-center gap-2 border-0"
                                        type="button" id="userDropdown" data-bs-toggle="dropdown">
                                        <i className="fa-solid fa-circle-user fa-lg text-primary"></i>
                                        <span>Account</span>
                                    </button>
                                    <ul className="dropdown-menu dropdown-menu-end shadow-lg">
                                        <li>
                                            <a className="dropdown-item text-light" href="#" onClick={openWalletModal}>
                                                <i className="fa-solid fa-wallet me-2 text-muted"></i>
                                                Wallet
                                            </a>
                                        </li>
                                        <li>
                                            <hr className="dropdown-divider border-secondary" />
                                        </li>
                                        <li>
                                            <button className="dropdown-item text-danger" onClick={handleLogout}>
                                                <i className="fa-solid fa-right-from-bracket me-2"></i> Logout
                                            </button>
                                        </li>
                                    </ul>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </nav>

            {/* Mobile Drawer Navigation */}
            {showDrawer && (
                <div className="mobile-drawer-backdrop" onClick={() => setShowDrawer(false)}></div>
            )}
            
            <div className={`mobile-drawer ${showDrawer ? 'show' : ''}`}>
                <div className="drawer-content">
                    <div className="drawer-header">
                        <h5 className="mb-0 font-archivo text-primary">
                            <i className="fa-solid fa-bars me-2"></i>Menu
                        </h5>
                        <button className="btn-close-drawer" onClick={() => setShowDrawer(false)}>
                            <i className="fa-solid fa-times"></i>
                        </button>
                    </div>

                    <div className="drawer-body">
                        {/* Network Selection */}
                        <div className="drawer-section">
                            <label className="drawer-label">
                                <i className="fa-solid fa-network-wired me-2"></i>Network
                            </label>
                            <div className="network-options">
                                <button 
                                    className={`network-option ${selectedNetwork === 'mainnet' ? 'active' : ''}`}
                                    onClick={() => handleNetworkChange('mainnet')}
                                >
                                    <i className="fa-solid fa-circle text-success me-2"></i>
                                    <span>Mainnet</span>
                                    {selectedNetwork === 'mainnet' && <i className="fa-solid fa-check ms-auto"></i>}
                                </button>
                                <button 
                                    className={`network-option ${selectedNetwork === 'devnet' ? 'active' : ''}`}
                                    onClick={() => handleNetworkChange('devnet')}
                                >
                                    <i className="fa-solid fa-circle text-warning me-2"></i>
                                    <span>Devnet</span>
                                    {selectedNetwork === 'devnet' && <i className="fa-solid fa-check ms-auto"></i>}
                                </button>
                                <button 
                                    className={`network-option ${selectedNetwork === 'testnet' ? 'active' : ''}`}
                                    onClick={() => handleNetworkChange('testnet')}
                                >
                                    <i className="fa-solid fa-circle text-info me-2"></i>
                                    <span>Testnet</span>
                                    {selectedNetwork === 'testnet' && <i className="fa-solid fa-check ms-auto"></i>}
                                </button>
                            </div>
                        </div>

                        <hr className="drawer-divider" />

                        {/* Menu Items */}
                        <div className="drawer-section">
                            <button className="drawer-menu-item" onClick={openWalletModal}>
                                <i className="fa-solid fa-wallet me-3"></i>
                                <span>Wallet</span>
                                <i className="fa-solid fa-chevron-right ms-auto"></i>
                            </button>

                            <button className="drawer-menu-item text-danger" onClick={handleLogout}>
                                <i className="fa-solid fa-right-from-bracket me-3"></i>
                                <span>Logout</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

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