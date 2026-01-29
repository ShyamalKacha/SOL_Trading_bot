import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { useWallet } from '../context/WalletContext';

import TradingGraph from '../components/TradingGraph';

const Dashboard = () => {
    const { user } = useAuth();

    const {
        walletAddress,
        balances,
        selectedNetwork,
        loading: loadingWallet,
        error: walletError,
        refreshWalletData
    } = useWallet();
    // // Wallet State
    // const [walletAddress, setWalletAddress] = useState('Connecting to Solana...');
    // const [balances, setBalances] = useState([]);
    // const [loadingWallet, setLoadingWallet] = useState(false);
    // const [walletError, setWalletError] = useState(null);

    // Funding State
    const [depositAmount, setDepositAmount] = useState('');
    const [showQR, setShowQR] = useState(false);
    const [withdrawAddress, setWithdrawAddress] = useState('');
    const [withdrawToken, setWithdrawToken] = useState('');
    const [withdrawAmount, setWithdrawAmount] = useState('');
    const [withdrawLoading, setWithdrawLoading] = useState(false);

    // Strategy Config State
    // const [network, setNetwork] = useState('mainnet'); // Removed in favor of global selectedNetwork
    const [tradingMode] = useState('automatic'); // Fixed to automatic
    const [selectedToken, setSelectedToken] = useState('So11111111111111111111111111111111111111112');
    const [customToken, setCustomToken] = useState('');
    const [tokenName, setTokenName] = useState('Solana'); // Track token name


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

    // Order Log State
    const [orders, setOrders] = useState([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [loadingOrders, setLoadingOrders] = useState(false);

    // Modal State
    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [confirmData, setConfirmData] = useState(null);

    // Clock
    const statusIntervalRef = useRef(null);

    // Initial Data Load
    // Initial Data Load
    useEffect(() => {
        refreshWalletData();
        fetchOrders(1);

        // Check trading status ONCE to see if bot is already running
        fetchTradingStatus();

        // Cleanup on unmount
        return () => {
            if (statusIntervalRef.current) {
                clearInterval(statusIntervalRef.current);
            }
        };
    }, []);

    // Start/Stop polling based on trading state
    useEffect(() => {
        // Clear any existing interval first
        if (statusIntervalRef.current) {
            clearInterval(statusIntervalRef.current);
            statusIntervalRef.current = null;
        }

        // Only start polling if bot is running
        if (isTrading) {
            statusIntervalRef.current = setInterval(fetchTradingStatus, 2000);
        }

        // Cleanup
        return () => {
            if (statusIntervalRef.current) {
                clearInterval(statusIntervalRef.current);
            }
        };
    }, [isTrading]);

    const fetchOrders = async (page = 1) => {
        setLoadingOrders(true);
        try {
            // Include network filter if needed, or backend handles it (backend uses user's history)
            const response = await axios.get(`/api/orders?page=${page}&per_page=15`);
            if (response.data.success) {
                setOrders(response.data.orders);
                setTotalPages(response.data.pagination.total_pages);
                setCurrentPage(page);
            }
        } catch (error) {
            console.error("Error fetching orders:", error);
        } finally {
            setLoadingOrders(false);
        }
    };

    const fetchTradingStatus = async () => {
        try {
            const response = await axios.get('/api/trading-status');
            const data = response.data;

            // Check if we need to refresh orders based on trade_count change
            // We use a ref or previous state comparison. Since we are inside the closure of the interval, 
            // relying on 'status' state might be tricky if it's stale. 
            // However, setStatus receives 'prev' which is current.
            // Better approach: Store last known trade_count in a separate ref or state that we can check.

            setStatus(prev => {
                // If trade_count changed, trigger order refresh
                if (data.trade_count !== undefined && data.trade_count !== prev.trade_count) {
                    // We need to call fetchOrders here, but we can't await it easily inside setState
                    // So we trigger it as a side effect.
                    setTimeout(() => fetchOrders(1), 0);
                }

                return {
                    ...prev,
                    ...data,
                    // Ensure dynamic_base_price is handled correctly
                    dynamic_base_price: data.dynamic_base_price !== undefined ? data.dynamic_base_price : (data.original_base_price || 0)
                };
            });

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
                if (data.selected_token) {
                    setSelectedToken(data.selected_token);
                    if (data.selected_token !== 'So11111111111111111111111111111111111111112') {
                        setCustomToken(data.selected_token);
                    }
                }
                // if (data.network) setNetwork(data.network); // No longer setting local network state
            }
        } catch (error) {
            console.error("Error fetching trading status", error);
        }
    };

    // Effect to resolve token name whenever selectedToken changes (e.g. from backend sync)
    useEffect(() => {
        const resolveName = async () => {
            if (selectedToken === 'So11111111111111111111111111111111111111112') {
                setTokenName('Solana');
                return;
            }
            try {
                const response = await axios.post('/api/resolve-token', { mint: selectedToken });
                if (response.data.success) {
                    setTokenName(response.data.symbol ? `${response.data.name} (${response.data.symbol})` : response.data.name);
                }
            } catch (err) {
                console.error("Auto-resolve token error:", err);
            }
        };
        resolveName();
    }, [selectedToken]);

    // const refreshWalletData = async () => {
    //     setLoadingWallet(true);
    //     setWalletError(null);
    //     try {
    //         // Get Wallet Info
    //         const infoResponse = await axios.get('/api/wallet-info');
    //         if (infoResponse.data.success) {
    //             setWalletAddress(infoResponse.data.wallet_address);
    //         } else {
    //             setWalletError(infoResponse.data.message);
    //             setWalletAddress('Error loading wallet');
    //         }

    //         // Get Balances
    //         const balanceResponse = await axios.get('/api/wallet-balance');
    //         if (balanceResponse.data.success) {
    //             setBalances(balanceResponse.data.balances);
    //         }
    //     } catch (error) {
    //         console.error("Wallet refresh error", error);
    //         setWalletError("Failed to sync chain data");
    //         setWalletAddress('Connection Failed');
    //     } finally {
    //         setLoadingWallet(false);
    //         toast.success("Chain data synchronized", { position: "bottom-right", theme: "dark" });
    //     }
    // };

    const copyToClipboard = (text, label) => {
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            toast.success(`${label} Copied`, { position: "bottom-right", theme: "dark" });
        }).catch(() => {
            toast.error("Failed to copy", { position: "bottom-right", theme: "dark" });
        });
    };

    const handleResolveToken = async () => {
        const tokenToResolve = customToken.trim();

        // If empty, revert to default SOL
        if (!tokenToResolve) {
            setSelectedToken('So11111111111111111111111111111111111111112');
            setTokenName('Solana');
            toast.info("Reverted to Default (SOL)", { position: "bottom-right", theme: "dark" });
            return;
        }

        try {
            const response = await axios.post('/api/resolve-token', { mint: tokenToResolve });
            if (response.data.success) {
                setSelectedToken(response.data.mint);
                setTokenName(response.data.symbol ? `${response.data.name} (${response.data.symbol})` : response.data.name);
                toast.success("Token Resolved Successfully", { position: "bottom-right", theme: "dark" });
            } else {
                toast.error(response.data.message || "Invalid Token", { position: "bottom-right", theme: "dark" });
            }
        } catch (error) {
            console.error("Token resolve error:", error);
            toast.error("Error resolving token", { position: "bottom-right", theme: "dark" });
        }
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
        // Reserve enough for:
        // 1. Transaction Fee for User Transfer (~0.000005)
        // 2. Transaction Fee for Fee Transfer (~0.000005)
        // 3. The 0.000005 fee deducted from user amount (part of the logic)
        // So safe buffer is slightly higher
        const RESERVED_BUFFER = 0.000015; // 3x standard fee just to be safe

        let max = token.balance;
        if (token.mint === SOL_MINT && max > RESERVED_BUFFER) {
            max -= RESERVED_BUFFER;
        }

        setWithdrawAmount(Math.max(0, max).toFixed(6));
    };

    const handleWithdraw = async () => {
        if (!withdrawAddress) {
            toast.warning("Please enter a destination address", { position: "bottom-right", theme: "dark" });
            return;
        }
        if (!withdrawToken) {
            toast.warning("Please select an asset to withdraw", { position: "bottom-right", theme: "dark" });
            return;
        }
        if (!withdrawAmount || parseFloat(withdrawAmount) <= 0) {
            toast.warning("Please enter a valid amount", { position: "bottom-right", theme: "dark" });
            return;
        }

        // Find selected token to get decimals
        const token = balances.find(b => b.mint === withdrawToken);
        if (!token) {
            toast.error("Selected token not found in wallet", { position: "bottom-right", theme: "dark" });
            return;
        }

        // --- FEE CALCULATION & CONFIRMATION ---
        const amount = parseFloat(withdrawAmount);
        const feePercentage = 0.05;
        const feeAmount = amount * feePercentage;
        let receiveAmount = amount - feeAmount;
        let feeDisplay = `${feeAmount.toFixed(6)}`;
        const SOL_MINT = "So11111111111111111111111111111111111111112";
        const isSol = withdrawToken === SOL_MINT;

        if (isSol) {
            // For SOL: Deduct extra 0.000005
            const extraFee = 0.000005;
            receiveAmount -= extraFee;
            feeDisplay = `${feeAmount.toFixed(6)} + ${extraFee.toFixed(6)}`;
        }

        if (receiveAmount <= 0) {
            toast.error("Amount must be greater than fees", { position: "bottom-right", theme: "dark" });
            return;
        }

        // Set Confirmation Data and Show Modal
        setConfirmData({
            receiveAmount: receiveAmount.toFixed(6),
            totalAmount: amount.toFixed(6),
            feeDisplay: feeDisplay,
            token: token.token,
            isSol: isSol,
            tokenDecimals: token.decimals
        });
        setShowConfirmModal(true);
    };

    const finalizeWithdraw = async () => {
        // Find selected token again to be safe, or use data from confirmData if preferred
        // We'll rely on state as minimal time passed

        setWithdrawLoading(true);
        try {
            const response = await axios.post('/api/withdraw-funds', {
                destination_address: withdrawAddress,
                amount: parseFloat(withdrawAmount),
                token_mint: withdrawToken,
                decimals: confirmData.tokenDecimals
            });

            if (response.data.success) {
                toast.success(`Withdrawal Successful: ${response.data.signature.substring(0, 8)}...`, { position: "bottom-right", theme: "dark" });
                setWithdrawAmount('');
                setWithdrawAddress('');
                refreshWalletData(); // Refresh balance
                setShowConfirmModal(false); // Close modal
            } else {
                toast.error(response.data.message || "Withdrawal failed", { position: "bottom-right", theme: "dark" });
            }
        } catch (error) {
            console.error("Withdrawal error:", error);
            const errorMsg = error.response?.data?.message || "Error processing withdrawal";
            toast.error(errorMsg, { position: "bottom-right", theme: "dark" });
        } finally {
            setWithdrawLoading(false);
        }
    };

    const startTrading = async () => {
        // Validation: If user typed a custom token but didn't resolve it (selectedToken doesn't match customToken)
        // We only check this if customToken is NOT empty. If empty, we assume default SOL (which selectedToken should be if initialized or reset)
        if (customToken.trim() && customToken.trim() !== selectedToken) {
            toast.warning("Please click ENTER to confirm your custom token address.", { position: "bottom-right", theme: "dark" });
            return;
        }

        let finalToken = selectedToken;


        if (validateParams()) {
            setTradingLoading(true);
            try {
                const config = {
                    upPercentage: parseFloat(upPercentage),
                    downPercentage: parseFloat(downPercentage),
                    selectedToken: finalToken,
                    tradeAmount: parseFloat(tradeAmount),
                    parts: parseInt(parts),
                    network: selectedNetwork,
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
                    <button className="btn btn-sm btn-outline-secondary" onClick={() => refreshWalletData()} disabled={loadingWallet} title="Sync Chain Data">
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

                            <button className="btn btn-danger w-100" onClick={handleWithdraw} disabled={withdrawLoading}>
                                {withdrawLoading ? (
                                    <><span className="spinner-border spinner-border-sm me-2"></span>Processing...</>
                                ) : (
                                    <><i className="fas fa-paper-plane me-2"></i>Execute Withdrawal</>
                                )}
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
                                <div className="input-group">
                                    <span className="input-group-text"><i className="fa-solid fa-network-wired"></i></span>
                                    <input type="text" className="form-control font-archivo fw-bold"
                                        value={selectedNetwork.toUpperCase()} disabled readOnly
                                        style={{ background: 'rgba(255, 255, 255, 0.05)', color: 'var(--text-main)' }} />
                                </div>
                                <div className="form-text mt-1">Network selected via Navbar</div>
                            </div>
                            <div className="mb-3">
                                <label className="form-label">Target Asset</label>
                                <div className="input-group mb-2">
                                    <input
                                        type="text"
                                        className="form-control font-archivo text-xs"
                                        placeholder="Default: SOL or Enter Mint Address"
                                        value={customToken}
                                        onChange={e => setCustomToken(e.target.value)}
                                    />
                                    <button className="btn btn-outline-primary font-archivo" type="button" onClick={handleResolveToken}>
                                        ENTER
                                    </button>
                                </div>
                                <div className="d-flex justify-content-between align-items-center">
                                    <small className="text-muted">Selected:</small>
                                    <span className="badge bg-primary bg-opacity-25 text-primary font-archivo">
                                        {tokenName}
                                    </span>
                                </div>
                                <div className="form-text mt-1 text-xs text-muted" style={{ fontSize: '0.7em', wordBreak: 'break-all' }}>
                                    {selectedToken}
                                </div>
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
                                {loadingOrders ? (
                                    <tr><td colSpan="8" className="text-center py-5 font-archivo">Loading orders...</td></tr>
                                ) : orders && orders.length > 0 ? (
                                    orders.map((tx, idx) => (
                                        <tr key={idx}>
                                            <td>{new Date(tx.timestamp).toLocaleString()}</td>
                                            <td><span className={`badge ${tx.network === 'mainnet' ? 'bg-primary' : 'bg-warning text-dark'}`}>{tx.network}</span></td>
                                            <td><span className={`badge ${tx.action === 'buy' ? 'bg-success' : 'bg-danger'}`}>{tx.action.toUpperCase()}</span></td>
                                            <td>{tx.amount ? `$${tx.amount.toFixed(4)}` : '-'}</td>
                                            <td>{tx.token_symbol}</td>
                                            <td>${typeof tx.price === 'number' ? tx.price.toFixed(4) : tx.price}</td>
                                            <td className={tx.pnl >= 0 ? 'text-success' : 'text-danger'}>
                                                {tx.pnl !== null ? (tx.pnl >= 0 ? '+' : '-') + '$' + Math.abs(tx.pnl).toFixed(4) : '-'}
                                            </td>
                                            <td><span className="badge bg-secondary">{tx.status ? tx.status.toUpperCase() : 'COMPLETED'}</span></td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan="8" className="text-center py-5 text-muted font-archivo">
                                            No orders found
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    {/* Mobile View - Cards */}
                    <div className="d-md-none p-3">
                        {loadingOrders ? (
                            <div className="text-center py-5 font-archivo">Loading orders...</div>
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
                                            {tx.pnl !== null ? (tx.pnl >= 0 ? '+' : '-') + '$' + Math.abs(tx.pnl).toFixed(4) : '-'}
                                        </div>
                                    </div>
                                    <div className="d-flex justify-content-between small text-muted">
                                        <span>Amt: {tx.amount ? `$${tx.amount.toFixed(4)}` : '-'}</span>
                                        <span>Price: ${typeof tx.price === 'number' ? tx.price.toFixed(4) : tx.price}</span>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="text-center py-5 text-muted">NO TRANSACTIONS RECORDED</div>
                        )}
                    </div>

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                        <div className="p-3 border-top border-secondary border-opacity-10 d-flex justify-content-between align-items-center">
                            <button className="btn btn-sm btn-outline-secondary"
                                onClick={() => fetchOrders(currentPage - 1)} disabled={currentPage === 1 || loadingOrders}>
                                <i className="fas fa-chevron-left me-1"></i> Prev
                            </button>
                            <span className="font-archivo small text-muted">Page {currentPage} of {totalPages}</span>
                            <button className="btn btn-sm btn-outline-secondary"
                                onClick={() => fetchOrders(currentPage + 1)} disabled={currentPage === totalPages || loadingOrders}>
                                Next <i className="fas fa-chevron-right ms-1"></i>
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Confirmation Modal */}
            {showConfirmModal && (
                <div className="modal-backdrop-custom d-flex align-items-center justify-content-center"
                    style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        zIndex: 1050
                    }}>
                    <div className="card glass-panel border-0 p-4" style={{ maxWidth: '400px', width: '90%', background: '#1a1a1a', border: '1px solid #333', borderRadius: '12px' }}>
                        <div className="text-center mb-4">
                            <i className="fas fa-exclamation-circle text-warning fa-3x mb-3"></i>
                            <h4 className="font-archivo fw-bold text-white">Confirm Withdrawal</h4>
                        </div>

                        <div className="mb-4">
                            <div className="d-flex justify-content-between mb-2">
                                <span className="text-muted">Receive Amount:</span>
                                <span className="text-white fw-bold">{confirmData?.receiveAmount} {confirmData?.token}</span>
                            </div>
                            <div className="d-flex justify-content-between mb-2">
                                <span className="text-muted">Fee Deducted:</span>
                                <span className="text-danger">{confirmData?.feeDisplay} {confirmData?.token}</span>
                            </div>
                            <div className="d-flex justify-content-between mt-3 pt-3 border-top border-secondary">
                                <span className="text-muted">Total Withdraw:</span>
                                <span className="text-white fw-bold">{confirmData?.totalAmount} {confirmData?.token}</span>
                            </div>
                            <div className="mt-2 text-center">
                                <small className="text-muted" style={{ fontSize: '0.8rem' }}>(Includes 5% Service Fee {confirmData?.isSol ? '+ Network Fee' : ''})</small>
                            </div>
                        </div>

                        <div className="d-grid gap-2 d-flex justify-content-center">
                            <button className="btn btn-outline-secondary px-4 py-2" onClick={() => setShowConfirmModal(false)}>
                                Cancel
                            </button>
                            <button className="btn btn-primary px-4 py-2" onClick={finalizeWithdraw} disabled={withdrawLoading}>
                                {withdrawLoading ? <span className="spinner-border spinner-border-sm me-2"></span> : 'Confirm'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
