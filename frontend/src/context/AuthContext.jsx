import { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const checkAuth = async () => {
            try {
                const response = await axios.get('/api/check-auth');
                if (response.data.authenticated) {
                    setUser({ id: response.data.user_id });
                } else {
                    setUser(null);
                }
            } catch (error) {
                console.log("Not authenticated");
                setUser(null);
            } finally {
                setLoading(false);
            }
        };

        checkAuth();
    }, []);

    const login = async (email, password) => {
        try {
            const response = await axios.post('/api/login', { email, password });
            if (response.data.success) {
                setUser({ email }); // You might want to get more user info here
                return { success: true };
            }
            return { success: false, message: response.data.message };
        } catch (error) {
            return { success: false, message: error.response?.data?.message || 'Login failed' };
        }
    };

    const register = async (email, password) => {
        try {
            const response = await axios.post('/api/register', { email, password });
            if (response.data.success) {
                // OTP logic might handle the next steps
                return { success: true, message: response.data.message };
            }
            return { success: false, message: response.data.message };
        } catch (error) {
            return { success: false, message: error.response?.data?.message || 'Registration failed' };
        }
    };

    const verifyOtp = async (email, otp) => {
        try {
            const response = await axios.post('/api/verify-otp', { email, otp });
            if (response.data.success) {
                return { success: true, message: response.data.message };
            }
            return { success: false, message: response.data.message };
        } catch (error) {
            return { success: false, message: error.response?.data?.message || 'Verification failed' };
        }
    };


    const logout = async () => {
        try {
            await axios.post('/api/logout');
            setUser(null);
        } catch (error) {
            console.error("Logout failed", error);
        }
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, verifyOtp, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
