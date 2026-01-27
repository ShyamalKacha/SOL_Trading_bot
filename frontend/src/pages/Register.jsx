import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Logo from "../assets/jumpsol-logo.png"

const Register = () => {
    const [step, setStep] = useState(1); // 1: Register, 2: OTP
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        confirmPassword: '',
        otp: ''
    });
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState(null);
    const { register, verifyOtp } = useAuth();
    const navigate = useNavigate();

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleRegister = async (e) => {
        e.preventDefault();
        setMessage(null);

        if (formData.password !== formData.confirmPassword) {
            setMessage({ type: 'danger', text: 'Passwords do not match' });
            return;
        }
        if (formData.password.length < 6) {
            setMessage({ type: 'danger', text: 'Password must be at least 6 characters' });
            return;
        }

        setLoading(true);
        const result = await register(formData.email, formData.password);
        setLoading(false);

        if (result.success) {
            setStep(2);
            setMessage({ type: 'info', text: `OTP sent to ${formData.email}` });
        } else {
            setMessage({ type: 'danger', text: result.message });
        }
    };

    const handleVerify = async (e) => {
        e.preventDefault(); // In case it's in a form
        setMessage(null);
        setLoading(true);

        const result = await verifyOtp(formData.email, formData.otp);
        setLoading(false);

        if (result.success) {
            setMessage({ type: 'success', text: 'Registration successful. Redirecting...' });
            setTimeout(() => {
                navigate('/login');
            }, 2000);
        } else {
            setMessage({ type: 'danger', text: result.message });
        }
    };

    return (
        <div className="container-fluid d-flex align-items-center justify-content-center min-vh-100">
            <div className="glass-panel w-100" style={{ maxWidth: '500px' }}>
                <div className="glass-header text-center justify-content-center py-4">
                    <div className="d-flex align-items-center">
                        <img src={Logo} alt="AutoSOL" height={40} />
                    </div>
                </div>

                <div className="glass-body p-4">
                    <h3 className="font-archivo text-center text-boss mb-4 tracking-wide">CREATE ACCOUNT</h3>

                    {step === 1 ? (
                        <form onSubmit={handleRegister}>
                            <div className="mb-3">
                                <label htmlFor="email" className="form-label">Email Address</label>
                                <div className="input-group input-group-white">
                                    <span className="input-group-text"><i className="fas fa-envelope"></i></span>
                                    <input
                                        type="email"
                                        className="form-control font-archivo"
                                        id="email"
                                        name="email"
                                        placeholder="name@domain.com"
                                        required
                                        value={formData.email}
                                        onChange={handleChange}
                                    />
                                </div>
                            </div>

                            <div className="mb-3">
                                <label htmlFor="password" className="form-label">Password</label>
                                <div className="input-group input-group-white">
                                    <span className="input-group-text"><i className="fas fa-lock"></i></span>
                                    <input
                                        type="password"
                                        className="form-control font-archivo"
                                        id="password"
                                        name="password"
                                        placeholder="••••••••"
                                        required
                                        value={formData.password}
                                        onChange={handleChange}
                                    />
                                </div>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="confirmPassword" className="form-label">Confirm Password</label>
                                <div className="input-group input-group-white">
                                    <span className="input-group-text"><i className="fas fa-check-double"></i></span>
                                    <input
                                        type="password"
                                        className="form-control font-archivo"
                                        id="confirmPassword"
                                        name="confirmPassword"
                                        placeholder="••••••••"
                                        required
                                        value={formData.confirmPassword}
                                        onChange={handleChange}
                                    />
                                </div>
                            </div>

                            <div className="d-grid mb-3">
                                <button type="submit" className="btn btn-primary btn-lg font-archivo" disabled={loading}>
                                    {loading ? (
                                        <><span className="spinner-border spinner-border-sm me-2"></span>PROCESSING...</>
                                    ) : (
                                        <><i className="fas fa-user-plus me-2"></i>REGISTER</>
                                    )}
                                </button>
                            </div>
                        </form>
                    ) : (
                        <div>
                            <div className="mb-4">
                                <label htmlFor="otp" className="form-label">One-Time Password (OTP)</label>
                                <div className="input-group">
                                    <span className="input-group-text"><i className="fas fa-shield-alt"></i></span>
                                    <input
                                        type="text"
                                        className="form-control font-archivo text-center fw-bold"
                                        id="otp"
                                        name="otp"
                                        required
                                        style={{ letterSpacing: '3px' }}
                                        value={formData.otp}
                                        onChange={handleChange}
                                    />
                                </div>
                            </div>
                            <div className="d-grid">
                                <button type="button" className="btn btn-success btn-lg font-archivo" onClick={handleVerify} disabled={loading}>
                                    {loading ? (
                                        <><span className="spinner-border spinner-border-sm me-2"></span>VERIFYING...</>
                                    ) : (
                                        <><i className="fas fa-check-circle me-2"></i>VERIFY OTP</>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}

                    {message && (
                        <div className={`alert alert-${message.type} font-archivo small mt-3`}>
                            {message.type === 'danger' && <i className="fas fa-exclamation-triangle me-2"></i>}
                            {message.type === 'success' && <i className="fas fa-check-double me-2"></i>}
                            {message.text}
                        </div>
                    )}

                    {step === 1 && (
                        <div className="text-center mt-3 pt-3 border-top border-secondary border-opacity-25">
                            <p className="text-muted small mb-0">Already have an account?
                                <Link to="/login" className="text-accent fw-bold font-archivo ms-1">Login</Link>
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Register;
