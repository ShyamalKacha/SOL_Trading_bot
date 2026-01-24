# AutoSOL - Multi-User Solana Trading Bot

A comprehensive multi-user Solana trading bot with a **modern React frontend**, **Flask API backend**, automated ladder trading, and real-time wallet management.

![Status](https://img.shields.io/badge/Status-Active-success)
![Frontend](https://img.shields.io/badge/Frontend-React_18_%2B_Vite-61DAFB)
![Backend](https://img.shields.io/badge/Backend-Python_Flask-000000)
![Blockchain](https://img.shields.io/badge/Network-Solana-9945FF)

## 🚀 Features

- **Modern UI**: specialized dark theme built with React & Bootstrap.
- **Multi-User Support**: Individual wallet and trading instances for every user.
- **Real-Time Dashboard**: Live price monitoring, wallet balances, and active trade status.
- **Automated Trading**: Advanced ladder trading algorithm with configurable strategies (Take Profit / Stop Loss).
- **Wallet Integration**:
    - Generates unique Solana wallets for users.
    - Supports SOL and SPL token deposits/withdrawals.
    - QR Code generation for easy funding.
- **Security**:
    - OTP Email Verification for registration.
    - Fernet (AES-128) encryption for private keys.
    - HttpOnly session management.

## 🛠 Architecture

The project is split into two distinct parts:

1.  **Backend (`/app`)**: A Python Flask API that handles business logic, database interactions, and blockchain transactions.
2.  **Frontend (`/frontend`)**: A React Single Page Application (SPA) built with Vite that consumes the API.

## 📋 Prerequisites

- **Python 3.10+**
- **Node.js 16+** & **npm**
- **MongoDB 6.0+** (Local or Atlas)
- **Solana API Key** (Helius recommended) & **Jupiter API Key**

## ⚡ Quick Start (Windows)

The easiest way to run the application is using the developer script:

1.  **Configure Environment**:
    Create a `.env` file in the root directory (see [Environment Variables](#-environment-variables)).

2.  **Run the App**:
    Double-click `run_dev.bat` or run it from the terminal:
    ```cmd
    run_dev.bat
    ```
    *   This will launch the Backend (Port 5000) and Frontend (Port 5173/5174) in separate windows.

## 📦 Manual Installation

### 1. Backend Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run API
python app/main.py
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run Development Server
npm run dev
```

## 🔑 Environment Variables

Create a `.env` file in the root directory:

```env
# Flask Settings
SECRET_KEY=your-super-secret-key-change-this

# Database
MONGO_URI=mongodb://localhost:27017/trading_bot

# Blockchain APIs
JUPITER_API_KEY=your_jupiter_api_key
HELIUS_API_KEY=your_helius_api_key

# Email Service (Gmail Example)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SENDER_EMAIL=your_email@gmail.com

# Security
ENCRYPTION_KEY=your_fernet_key
```

> **Tip**: Generate an encryption key using: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## 🖥 Usage Guide

1.  **Register/Login**: Create an account and verify via Email OTP.
2.  **Dashboard**:
    *   **Wallet Operations**: View your generated address. Send SOL to this address to fund the bot.
    *   **Strategy Config**: Select network (Mainnet/Devnet), target token (e.g., SOL, USDC, JUP), and trade execution parameters.
    *   **Live Monitor**: Watch real-time P&L changes and active status.
3.  **Start Trading**: Click "INITIATE SEQUENCE" to begin the automated ladder strategy.
4.  **History**: View all past trades in the "Trade History" section.