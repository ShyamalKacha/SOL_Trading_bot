import { createContext, useState, useEffect, useContext, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from './AuthContext';

const WalletContext = createContext(null);

export const WalletProvider = ({ children }) => {
    const { user } = useAuth();
    
    // Wallet State
    const [walletAddress, setWalletAddress] = useState('Connecting to Solana...');
    const [balances, setBalances] = useState([]);
    const [selectedNetwork, setSelectedNetwork] = useState('mainnet');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    // Derived balances for quick access
    const [solBalance, setSolBalance] = useState(0);
    const [usdcBalance, setUsdcBalance] = useState(0);

    // Refresh wallet data - memoized to prevent unnecessary re-renders
    const refreshWalletData = useCallback(async (network = selectedNetwork) => {
        if (!user) return;
        
        setLoading(true);
        setError(null);
        console.log(network,"network");
        
        try {
            // Fetch wallet info (only once, address doesn't change)
            if (walletAddress === 'Connecting to Solana...') {
                const infoResponse = await axios.get('/api/wallet-info');
                if (infoResponse.data.success) {
                    setWalletAddress(infoResponse.data.wallet_address);
                } else {
                    setError(infoResponse.data.message);
                    setWalletAddress('Error loading wallet');
                }
            }

            // Fetch balances with network parameter
            const balanceResponse = await axios.get(`/api/wallet-balance?network=${network}`);
            if (balanceResponse.data.success) {
                setBalances(balanceResponse.data.balances);
                
                // Calculate SOL and USDC balances for quick access
                let sol = 0;
                let usdc = 0;
                balanceResponse.data.balances.forEach(b => {
                    if (b.token === 'SOL') sol = b.balance;
                    if (b.token === 'USDC') usdc = b.balance;
                });
                setSolBalance(sol);
                setUsdcBalance(usdc);
            } else {
                setError(balanceResponse.data.message);
            }
        } catch (err) {
            console.error("Wallet refresh error", err);
            setError("Failed to sync chain data");
        } finally {
            setLoading(false);
        }
    }, [user, selectedNetwork, walletAddress]);

    // Change network and refresh balances
    const changeNetwork = useCallback((network) => {
        setSelectedNetwork(network);
        // Balances will auto-refresh via useEffect
    }, []);

    // Initial load and periodic refresh
    useEffect(() => {
        if (user) {
            refreshWalletData();
            
            // Auto-refresh every 30 seconds
            const interval = setInterval(() => refreshWalletData(), 30000);
            return () => clearInterval(interval);
        }
    }, [user, refreshWalletData]);

    // Refresh when network changes
    useEffect(() => {
        if (user && selectedNetwork) {
            refreshWalletData(selectedNetwork);
        }
    }, [selectedNetwork, user]);

    const value = {
        // State
        walletAddress,
        balances,
        selectedNetwork,
        loading,
        error,
        solBalance,
        usdcBalance,
        
        // Actions
        refreshWalletData,
        changeNetwork,
    };

    return (
        <WalletContext.Provider value={value}>
            {children}
        </WalletContext.Provider>
    );
};

export const useWallet = () => {
    const context = useContext(WalletContext);
    if (!context) {
        throw new Error('useWallet must be used within WalletProvider');
    }
    return context;
};