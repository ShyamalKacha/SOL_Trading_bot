import React, { useEffect, useState } from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';

const Layout = () => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [solBalance, setSolBalance] = useState(0);
    const [usdcBalance, setUsdcBalance] = useState(0);

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

    return (
        <>
            {/* Navbar */}
            <nav className="navbar navbar-expand-lg fixed-top navbar-custom">
                <div className="container-xl">
                    <Link className="navbar-brand d-flex align-items-center gap-2" to="/dashboard">
                        <i className="fa-brands fa-solana text-primary fa-lg"></i>
                        <span className="tracking-tight">Auto<span className="text-primary">SOL</span></span>
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
                                            <span className="small font-mono text-muted">MAINNET</span>
                                        </div>
                                        <div className="vr h-50 my-auto text-muted opacity-25"></div>
                                        <div className="d-flex align-items-center gap-2" title="SOL Balance">
                                            <i className="fa-brands fa-solana text-primary small"></i>
                                            <span className="small font-mono text-light">{solBalance.toFixed(3)} SOL</span>
                                        </div>
                                        <div className="d-flex align-items-center gap-2" title="USDC Balance">
                                            <i className="fa-solid fa-dollar-sign text-success small"></i>
                                            <span className="small font-mono text-light">{usdcBalance.toFixed(2)} USDC</span>
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
                                                <a className="dropdown-item text-light" href="#" onClick={(e) => e.preventDefault()}>
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
        </>
    );
};

export default Layout;
