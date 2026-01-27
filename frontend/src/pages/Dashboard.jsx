import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import TradingGraph from '../components/TradingGraph';

const Dashboard = () => {
    const { user } = useAuth();


    // Wallet State
    const [walletAddress, setWalletAddress] = useState('Connecting to Solana...');
    const [balances, setBalances] = useState([]);
    const [loadingWallet, setLoadingWallet] = useState(false);
    const [walletError, setWalletError] = useState(null);

    // Funding State
    const [depositAmount, setDepositAmount] = useState('');
    const [showQR, setShowQR] = useState(false);
    const [withdrawAddress, setWithdrawAddress] = useState('');
    const [withdrawToken, setWithdrawToken] = useState('');
    const [withdrawAmount, setWithdrawAmount] = useState('');
    const [withdrawLoading, setWithdrawLoading] = useState(false);

    // Strategy Config State
    const [network, setNetwork] = useState('mainnet');
    const [tradingMode] = useState('automatic'); // Fixed to automatic
    const [selectedToken, setSelectedToken] = useState('So11111111111111111111111111111111111111112');
    const [customToken, setCustomToken] = useState('');

    // Execution Params State
    const [upPercentage, setUpPercentage] = useState(5);
    const [downPercentage, setDownPercentage] = useState(3);
    const [tradeAmount, setTradeAmount] = useState(10);
    const [parts, setParts] = useState(1);
    const [isTrading, setIsTrading] = useState(false);
    const [tradingLoading, setTradingLoading] = useState(false);

    // Live Monitor State
    const [status, setStatus] = useState({
        isRunning: false,
        current_price: 0,
        dynamic_base_price: 0,
        total_profit: 0,
        last_action: 'NONE',
        transaction_history: []
    });

    // Clock


    // Initial Data Load
    useEffect(() => {
        refreshWalletData();
        // Start polling trading status
        const statusInterval = setInterval(fetchTradingStatus, 2000);
        return () => clearInterval(statusInterval);
    }, []);

    const fetchTradingStatus = async () => {
        try {
            const response = await axios.get('/api/trading-status');
            const data = response.data;
            setStatus(prev => ({
                ...prev,
                ...data,
                // Ensure dynamic_base_price is handled correctly
                dynamic_base_price: data.dynamic_base_price !== undefined ? data.dynamic_base_price : (data.original_base_price || 0)
            }));

            // Sync local isTrading state with backend
            if (data.is_running !== undefined) {
                setIsTrading(data.is_running);
            }

            // Restore configuration if bot is running or has data
            if (data.is_running) {
                if (data.up_percentage) setUpPercentage(data.up_percentage);
                if (data.down_percentage) setDownPercentage(data.down_percentage);
                if (data.trade_amount) setTradeAmount(data.trade_amount);
                if (data.parts) setParts(data.parts);
                if (data.selected_token) setSelectedToken(data.selected_token);
                if (data.network) setNetwork(data.network);
            }
        } catch (error) {
            console.error("Error fetching trading status", error);
        }
    };

    const refreshWalletData = async () => {
        setLoadingWallet(true);
        setWalletError(null);
        try {
            // Get Wallet Info
            const infoResponse = await axios.get('/api/wallet-info');
            if (infoResponse.data.success) {
                setWalletAddress(infoResponse.data.wallet_address);
            } else {
                setWalletError(infoResponse.data.message);
                setWalletAddress('Error loading wallet');
            }

            // Get Balances
            const balanceResponse = await axios.get('/api/wallet-balance');
            if (balanceResponse.data.success) {
                setBalances(balanceResponse.data.balances);
            }
        } catch (error) {
            console.error("Wallet refresh error", error);
            setWalletError("Failed to sync chain data");
            setWalletAddress('Connection Failed');
        } finally {
            setLoadingWallet(false);
            toast.success("Chain data synchronized", { position: "bottom-right", theme: "dark" });
        }
    };

    const copyToClipboard = (text, label) => {
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            toast.success(`${label} Copied`, { position: "bottom-right", theme: "dark" });
        }).catch(() => {
            toast.error("Failed to copy", { position: "bottom-right", theme: "dark" });
        });
    };

    const handleGenerateQR = () => {
        if (!depositAmount || parseFloat(depositAmount) <= 0) {
            toast.warning("Please enter a valid amount", { position: "bottom-right", theme: "dark" });
            return;
        }
        setShowQR(true);
        toast.info("QR Code Generated", { position: "bottom-right", theme: "dark" });
    };

    const getSolanaPayUrl = () => {
        if (!walletAddress || !depositAmount) return "";
        const label = encodeURIComponent("AutoSOL Funding");
        const message = encodeURIComponent("Deposit to Trading Bot");
        return `solana:${walletAddress}?amount=${depositAmount}&label=${label}&message=${message}`;
    };

    const handleMaxWithdraw = () => {
        if (!withdrawToken) {
            toast.warning("Select an asset first", { position: "bottom-right", theme: "dark" });
            return;
        }

        const token = balances.find(b => b.mint === withdrawToken);
        if (!token) return;

        const SOL_MINT = "So11111111111111111111111111111111111111112";
        const TRANSACTION_FEE = 0.000005;

        let max = token.balance;
        if (token.mint === SOL_MINT && max > TRANSACTION_FEE) {
            max -= TRANSACTION_FEE;
        }

        setWithdrawAmount(Math.max(0, max).toFixed(6));
    };

    const handleWithdraw = () => {
        // Implement withdraw API call here if it existed in the original code,
        // but looking at `dashboard/index.html` logic, it called `withdrawFunds()` which wasn't fully shown 
        // in the `main.py` provided.
        // Assuming there isn't a backend endpoint for this in the provided `main.py` slice, 
        // I will just show a toast for now or check if I missed it.
        // Actually, I don't see `/api/withdraw` in the `main.py` snippet I read.
        // I will assume it's a placeholder or verify `main.py` again.
        // Checking `main.py` again... `api/withdraw` is NOT there. 
        // So I'll just put a placeholder toast.
        toast.info("Withdrawal functionality requires backend implementation.", { position: "bottom-right", theme: "dark" });
    };

    const startTrading = async () => {
        let finalToken = selectedToken;
        if (customToken.trim()) {
            if (customToken.length >= 32 && customToken.length <= 44) {
                finalToken = customToken;
            } else {
                toast.warning("Invalid Custom Token Address", { position: "bottom-right", theme: "dark" });
                return;
            }
        }

        if (validateParams()) {
            setTradingLoading(true);
            try {
                const config = {
                    upPercentage: parseFloat(upPercentage),
                    downPercentage: parseFloat(downPercentage),
                    selectedToken: finalToken,
                    tradeAmount: parseFloat(tradeAmount),
                    parts: parseInt(parts),
                    network,
                    tradingMode
                };

                const response = await axios.post('/api/start-trading', config);
                if (response.status === 200) {
                    toast.success("Trading Sequence Initiated", { position: "bottom-right", theme: "dark" });
                    setIsTrading(true);
                }
            } catch (error) {
                const errorMessage = error.response?.data?.error || error.response?.data?.message || "Failed to start trading";
                toast.error(errorMessage, { position: "bottom-right", theme: "dark" });
            } finally {
                setTradingLoading(false);
            }
        }
    };

    const stopTrading = async () => {
        setTradingLoading(true);
        try {
            await axios.post('/api/stop-trading');
            toast.info("Trading Sequence Terminated", { position: "bottom-right", theme: "dark" });
            setIsTrading(false);
        } catch (error) {
            toast.error("Error stopping trading", { position: "bottom-right", theme: "dark" });
        } finally {
            setTradingLoading(false);
        }
    };

    const validateParams = () => {
        if (parseFloat(tradeAmount) <= 0) { toast.warning("Trade amount must be > 0"); return false; }
        if (parseInt(parts) <= 0) { toast.warning("Parts must be > 0"); return false; }
        return true;
    };

    return (
        <div className="container-xl pb-5">
            <ToastContainer />
            {/* Wallet Command Center */}
            <div className="dash-panel">
                <div className="dash-header">
                    <div className="d-flex align-items-center gap-2">
                        <i className="fa-solid fa-wallet text-primary"></i>
                        <h5 className="font-archivo tracking-tight">WALLET OPERATIONS</h5>
                    </div>
                    <button className="btn btn-sm btn-outline-secondary" onClick={refreshWalletData} disabled={loadingWallet} title="Sync Chain Data">
                        <i className={`fas fa-sync-alt me-1 ${loadingWallet ? 'fa-spin' : ''}`}></i> SYNC
                    </button>
                </div>
                <div className="glass-body">
                    <div className="row g-4">
                        {/* Wallet ID */}
                        <div className="col-lg-5">
                            <label className="form-label">Wallet Address</label>
                            <div className="input-group mb-3">
                                <div className="wallet-address flex-grow-1 font-archivo text-primary" style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {walletAddress}
                                </div>
                                <button className="btn btn-outline-secondary copy-btn" type="button"
                                    onClick={() => copyToClipboard(walletAddress, 'Address')} title="Copy Address">
                                    <i className="fas fa-copy"></i>
                                </button>
                            </div>
                            {walletError && <div className="alert alert-danger py-2 mt-2">{walletError}</div>}
                        </div>

                        {/* Portfolio Overview */}
                        <div className="col-lg-7">
                            <label className="form-label">Asset Allocation</label>
                            <div className="rounded p-0" style={{ minHeight: '100px' }}>
                                {loadingWallet ? (
                                    <div className="text-center py-4 text-muted">
                                        <div className="spinner-border spinner-border-sm text-primary mb-2" role="status"></div>
                                        <div className="font-archivo small">SCANNING ASSETS...</div>
                                    </div>
                                ) : balances.length > 0 ? (
                                    <div className="table-responsive" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                        <table className="table mb-0">
                                            <thead>
                                                <tr>
                                                    <th>Asset</th>
                                                    <th className="text-end">Holding</th>
                                                </tr>
                                            </thead>
                                            <tbody className="font-archivo">
                                                {balances.map((b, idx) => (
                                                    <tr key={idx}>
                                                        <td>
                                                            <div className="d-flex align-items-center">
                                                                <div className="token-icon">{b.token.substring(0, 2)}</div>
                                                                <div>
                                                                    <div className="fw-bold">{b.token}</div>
                                                                    <small className="text-muted" style={{ fontSize: '0.75rem' }}>{b.name || 'Unknown'}</small>
                                                                </div>
                                                            </div>
                                                        </td>
                                                        <td className="text-end font-archivo">{b.balance.toFixed(6)}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                ) : (
                                    <div className="text-center py-4 text-muted">
                                        <i className="fas fa-wallet fa-2x mb-2 opacity-50"></i>
                                        <div>No assets detected</div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Funding Operations */}
            <div className="dash-panel">
                <div className="dash-header">
                    <div className="d-flex align-items-center gap-2">
                        <i className="fa-solid fa-money-bill-transfer text-success"></i>
                        <h5 className="font-archivo tracking-tight">FUNDING OPERATIONS</h5>
                    </div>
                </div>
                <div className="glass-body border-top border-secondary border-opacity-10">
                    <div className="row g-4">
                        {/* Deposit */}
                        <div className="col-md-6 border-end border-secondary border-opacity-10">

                            <div className="mb-3">
                                <label className="form-label">Deposit SOL</label>
                                <div className="input-group">
                                    <span className="input-group-text">SOL</span>
                                    <input type="number" className="form-control font-archivo" placeholder="0.00" min="0" step="0.01"
                                        value={depositAmount} onChange={e => setDepositAmount(e.target.value)} />
                                </div>
                            </div>

                            {showQR && (
                                <div className="d-flex flex-column align-items-center mb-3">
                                    <div className="bg-black p-3 rounded mb-2">
                                        <QRCodeSVG fgColor="white" bgColor="black" value={getSolanaPayUrl()} size={150} />
                                    </div>
                                    <div className="text-center text-muted small">Scan with your Solana Wallet</div>
                                </div>
                            )}

                            <button className="btn btn-success w-100" onClick={handleGenerateQR}>
                                <i className="fas fa-qrcode me-2"></i>Generate QR Code
                            </button>
                        </div>

                        {/* Withdraw */}
                        <div className="col-md-6">

                            <div className="mb-3">
                                <label className="form-label">Destination Address</label>
                                <input type="text" className="form-control font-archivo" placeholder="Solana Wallet Address"
                                    value={withdrawAddress} onChange={e => setWithdrawAddress(e.target.value)} />
                            </div>

                            <div className="row g-2 mb-3">
                                <div className="col-8">
                                    <label className="form-label">Asset</label>
                                    <select className="form-select font-archivo" value={withdrawToken} onChange={e => setWithdrawToken(e.target.value)}>
                                        <option value="" disabled>Select Token...</option>
                                        {balances.length > 0 && balances.map((b, idx) => (
                                            <option key={idx} value={b.mint}>{b.token} ({b.balance.toFixed(4)})</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="col-4">
                                    <label className="form-label">Amount</label>
                                    <div className="input-group">
                                        <input type="number" className="form-control font-archivo" placeholder="0.00"
                                            value={withdrawAmount} onChange={e => setWithdrawAmount(e.target.value)} />
                                        <button className="btn btn-outline-secondary font-archivo" type="button" onClick={handleMaxWithdraw}>MAX</button>
                                    </div>
                                </div>
                            </div>

                            <button className="btn btn-danger w-100" onClick={handleWithdraw}>
                                <i className="fas fa-paper-plane me-2"></i>Execute Withdrawal
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Trading Engine Grid */}
            <div className="row g-4 mb-4">
                {/* Configuration */}
                <div className="col-lg-4">
                    <div className="dash-panel h-100">
                        <div className="dash-header">
                            <div className="d-flex align-items-center gap-2">
                                <i className="fa-solid fa-sliders text-accent"></i>
                                <h5 className="font-archivo tracking-tight">STRATEGY CONFIG</h5>
                            </div>
                        </div>
                        <div className="glass-body">
                            <div className="mb-3">
                                <label className="form-label">Environment</label>
                                <select className="form-select font-archivo" value={network} onChange={e => setNetwork(e.target.value)}>
                                    <option value="mainnet">Mainnet (Live)</option>
                                    <option value="devnet">Devnet (Simulation)</option>
                                    <option value="testnet">Testnet (Beta)</option>
                                </select>
                            </div>
                            <div className="mb-3">
                                <label className="form-label">Target Asset</label>
                                <select className="form-select font-archivo mb-2" value={selectedToken} onChange={e => setSelectedToken(e.target.value)}>
                                    <option value="So11111111111111111111111111111111111111112">SOL - Native Solana</option>
                                    <option value="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v">USDC - USD Coin</option>
                                    <option value="4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R">RAY - Raydium</option>
                                    <option value="JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN">JUP - Jupiter</option>
                                </select>
                                <input type="text" className="form-control font-archivo text-xs"
                                    placeholder="Or paste Custom Mint Address"
                                    value={customToken} onChange={e => setCustomToken(e.target.value)} />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Execution Params */}
                <div className="col-lg-4">
                    <div className="dash-panel h-100">
                        <div className="dash-header">
                            <div className="d-flex align-items-center gap-2">
                                <i className="fa-solid fa-microchip text-warning"></i>
                                <h5 className="font-archivo tracking-tight">EXECUTION PARAMS</h5>
                            </div>
                        </div>
                        <div className="glass-body">
                            <div className="row g-2 mb-3">
                                <div className="col-6">
                                    <label className="form-label text-success">Take Profit (%)</label>
                                    <input type="number" className="form-control font-archivo" min="0" step="0.1"
                                        value={upPercentage} onChange={e => setUpPercentage(e.target.value)} disabled={isTrading} />
                                </div>
                                <div className="col-6">
                                    <label className="form-label text-danger">Stop Loss (%)</label>
                                    <input type="number" className="form-control font-archivo" min="0" step="0.1"
                                        value={downPercentage} onChange={e => setDownPercentage(e.target.value)} disabled={isTrading} />
                                </div>
                            </div>

                            <div className="mb-3">
                                <label className="form-label">Trade Volume (USD)</label>
                                <div className="input-group">
                                    <span className="input-group-text">$</span>
                                    <input type="number" className="form-control font-archivo fw-bold" min="0" step="0.01"
                                        value={tradeAmount} onChange={e => setTradeAmount(e.target.value)} disabled={isTrading} />
                                </div>
                            </div>

                            <div className="mb-4">
                                <label className="form-label">Order Splitting (Parts)</label>
                                <input type="number" className="form-control font-archivo" min="1" step="1"
                                    value={parts} onChange={e => setParts(e.target.value)} disabled={isTrading} />
                                <div className="form-text mt-1">Split volume into smaller orders.</div>
                            </div>

                            <div className="d-grid gap-2">
                                {!isTrading ? (
                                    <button className="btn btn-success py-3" onClick={startTrading} disabled={tradingLoading}>
                                        {tradingLoading ? <span className="spinner-border spinner-border-sm me-2"></span> : <i className="fa-solid fa-play me-2"></i>}
                                        INITIATE SEQUENCE
                                    </button>
                                ) : (
                                    <button className="btn btn-danger py-3" onClick={stopTrading} disabled={tradingLoading}>
                                        {tradingLoading ? <span className="spinner-border spinner-border-sm me-2"></span> : <i className="fa-solid fa-stop me-2"></i>}
                                        TERMINATE SEQUENCE
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Live Monitor */}
                <div className="col-lg-4">
                    <div className="dash-panel h-100">
                        <div className="dash-header">
                            <div className="d-flex align-items-center gap-2">
                                <i className="fa-solid fa-satellite-dish text-info"></i>
                                <h5 className="font-archivo tracking-tight">LIVE MONITOR</h5>
                            </div>
                        </div>
                        <div className="glass-body">
                            <div className="d-flex align-items-center justify-content-between mb-4 p-3 rounded"
                                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--glass-border)' }}>
                                <div>
                                    <div className="text-boss small text-uppercase">Engine Status</div>
                                    <div className="d-flex align-items-center mt-1">
                                        <span className={`status-indicator ${isTrading ? 'status-active' : 'status-inactive'}`}></span>
                                        <span className={`font-archivo fw-bold ${isTrading ? 'text-success' : 'text-muted'}`}>
                                            {isTrading ? 'ACTIVE' : 'STANDBY'}
                                        </span>
                                    </div>
                                </div>
                                <div className="text-end">
                                    <div className="text-boss small text-uppercase">Current Price</div>
                                    <div className="price-display text-primary">
                                        ${status.current_price < 0.01 ? status.current_price.toFixed(8) : status.current_price.toFixed(4)}
                                    </div>
                                </div>
                            </div>

                            <div className="row g-3 mb-3">
                                <div className="col-6">
                                    <div className="p-2 rounded bg-opacity-10 bg-white">
                                        <label className="small text-boss d-block">Base Price</label>
                                        <span className="font-archivo fw-bold">
                                            {status.dynamic_base_price ? (status.dynamic_base_price < 0.01 ? status.dynamic_base_price.toFixed(8) : status.dynamic_base_price.toFixed(4)) : '--'}
                                        </span>
                                    </div>
                                </div>
                                <div className="col-6">
                                    <div className="p-2 rounded bg-opacity-10 bg-white">
                                        <label className="small text-boss d-block">Dynamic Base</label>
                                        <span className="font-archivo fw-warning">
                                            ${status.dynamic_base_price ? (status.dynamic_base_price < 0.01 ? status.dynamic_base_price.toFixed(8) : status.dynamic_base_price.toFixed(4)) : '0.00'}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div className="p-3 rounded text-center mb-3"
                                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--glass-border)' }}>
                                <label className="text-boss small text-uppercase mb-1">Cumulative P&L</label>
                                <div className={`display-6 font-archivo fw-bold ${status.total_profit > 0 ? 'text-success' : status.total_profit < 0 ? 'text-danger' : 'text-muted'}`}>
                                    {status.total_profit >= 0 ? '+' : '-'}${Math.abs(status.total_profit).toFixed(4)}
                                </div>
                            </div>

                            <div className="d-flex justify-content-between align-items-center">
                                <span className="text-boss small">Last Action</span>
                                <span className={`badge font-archivo ${status.last_action?.includes('buy') ? 'bg-success' : status.last_action?.includes('sell') ? 'bg-danger' : 'bg-secondary'}`}>
                                    {status.last_action ? status.last_action.toUpperCase() : 'NONE'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Trading Graph */}
            <div className="dash-panel mb-4">
                <div className="dash-header d-flex justify-content-between align-items-center">
                    <div className="d-flex align-items-center gap-2">
                        <i className="fa-solid fa-chart-line text-warning"></i>
                        <h5 className="font-archivo tracking-tight mb-0">PERFORMANCE GRAPH</h5>
                    </div>
                </div>
                <div className="glass-body">
                    <TradingGraph
                        transactionHistory={status.transaction_history}
                        basePrice={status.dynamic_base_price || 0}
                    />
                </div>
            </div>


            {/* Order Log */}
            <div className="dash-panel">
                <div className="dash-header d-flex justify-content-between align-items-center">
                    <div className="d-flex align-items-center gap-2">
                        <i className="fa-solid fa-list-ul text-white"></i>
                        <h5 className="font-archivo tracking-tight mb-0">ORDER LOG</h5>
                    </div>
                    <Link to="/trade-history" className="btn btn-sm btn-outline-info font-archivo">
                        <i className="fa-solid fa-clock-rotate-left me-1"></i> View Past Trade
                    </Link>
                </div>
                <div className="glass-body p-0">
                    <div className="table-responsive">
                        <table className="table table-hover mb-0">
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>Action</th>
                                    <th>Part</th>
                                    <th>Asset</th>
                                    <th>Exec Price</th>
                                    <th>Base Price</th>
                                    <th>P&L</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {status.transaction_history && status.transaction_history.length > 0 ? (
                                    status.transaction_history.map((tx, idx) => (
                                        <tr key={idx}>
                                            <td>{tx.timestamp}</td>
                                            <td><span className={`badge ${tx.action === 'buy' ? 'bg-success' : 'bg-danger'}`}>{tx.action.toUpperCase()}</span></td>
                                            <td>{tx.part_number}/{tx.total_parts}</td>
                                            <td>{tx.token_symbol}</td>
                                            <td>${typeof tx.price === 'number' ? tx.price.toFixed(4) : tx.price}</td>
                                            <td>${tx.base_price_at_execution ? tx.base_price_at_execution.toFixed(4) : '0.00'}</td>
                                            <td className={tx.pnl >= 0 ? 'text-success' : 'text-danger'}>
                                                {tx.pnl ? (tx.pnl >= 0 ? '+' : '') + '$' + Math.abs(tx.pnl).toFixed(4) : '-'}
                                            </td>
                                            <td><span className="badge bg-secondary">{tx.status ? tx.status.toUpperCase() : 'COMPLETED'}</span></td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan="8" className="text-center py-5 text-muted font-archivo">
                                            NO TRANSACTIONS RECORDED
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
