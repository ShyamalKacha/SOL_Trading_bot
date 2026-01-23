import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Login = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [message, setMessage] = useState(null);
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setMessage(null);

        const result = await login(email, password);

        if (result.success) {
            navigate('/dashboard');
        } else {
            setMessage({ type: 'danger', text: result.message });
            setLoading(false);
        }
    };

    return (
        <div className="container-fluid d-flex align-items-center justify-content-center min-vh-100">
            <div className="glass-panel w-100" style={{ maxWidth: '450px' }}>
                <div className="glass-header text-center justify-content-center py-4">
                    <div className="d-flex align-items-center gap-2">
                        <i className="fa-brands fa-solana text-primary fa-2x"></i>
                        <span className="tracking-tight h4 mb-0">Auto<span className="text-primary">SOL</span></span>
                    </div>
                </div>

                <div className="glass-body p-4">
                    <h5 className="font-mono text-center text-muted mb-4 tracking-wide">LOGIN</h5>

                    <form onSubmit={handleSubmit}>
                        <div className="mb-4">
                            <label htmlFor="email" className="form-label">Email Address</label>
                            <div className="input-group">
                                <span className="input-group-text"><i className="fas fa-envelope"></i></span>
                                <input
                                    type="email"
                                    className="form-control font-mono"
                                    id="email"
                                    placeholder="name@domain.com"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="mb-4">
                            <label htmlFor="password" className="form-label">Password</label>
                            <div className="input-group">
                                <span className="input-group-text"><i className="fas fa-key"></i></span>
                                <input
                                    type="password"
                                    className="form-control font-mono"
                                    id="password"
                                    placeholder="••••••••"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="d-grid mb-4">
                            <button type="submit" className="btn btn-primary btn-lg font-mono" disabled={loading}>
                                {loading ? (
                                    <><span className="spinner-border spinner-border-sm me-2"></span>LOGGING IN...</>
                                ) : (
                                    <><i className="fas fa-sign-in-alt me-2"></i>LOGIN</>
                                )}
                            </button>
                        </div>
                    </form>

                    {message && (
                        <div className={`alert alert-${message.type} font-mono small`}>
                            <i className="fas fa-exclamation-triangle me-2"></i>{message.text}
                        </div>
                    )}

                    <div className="text-center mt-3 pt-3 border-top border-secondary border-opacity-25">
                        <p className="text-muted small mb-0">Don't have an account?
                            <Link to="/register" className="text-accent fw-bold font-mono ms-1">Register</Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Login;
