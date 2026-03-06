# 📈 Live Option Chain Dashboard (Fyers API v3)

A real-time, interactive Option Chain analysis web application built entirely in Python using **Streamlit** and the **Fyers API v3**. This dashboard is designed for derivative traders to analyze NIFTY 50, BANK NIFTY, and SENSEX options data seamlessly without writing complex front-end code.

## 🚀 Features

* **Real-Time Data Sync:** Fetches live option chain data including Open Interest (OI), Volume, Last Traded Price (LTP), and Implied Volatility (IV).
* **Multi-Index Support:** Easily switch between NIFTY 50, BANK NIFTY, and SENSEX.
* **Dynamic Expiry Selection:** Automatically fetches all available upcoming expiries from the Fyers server.
* **Smart Option Chain Table:** Combined view of Call and Put options with the **At-The-Money (ATM)** strike dynamically highlighted in yellow.
* **Live PCR Ratios:** Instant calculation of Volume PCR, OI PCR, Change in Volume PCR, and Change in OI PCR.
* **5-Minute Snapshot Log:** Automatically records the 'Change OI PCR' every 5 minutes and plots a live line chart for trend analysis.
* **Secure Login:** Pass your Client ID and Access Token securely via the UI sidebar (no hardcoded credentials).

## 🛠️ Technology Stack

* **Language:** Python 3.9+
* **Frontend/Framework:** [Streamlit](https://streamlit.io/)
* **Data Manipulation:** Pandas
* **Broker API:** Fyers API v3 (`fyers-apiv3`)

## ⚙️ How to Run Locally

**1. Clone the repository**
```bash
git clone https://github.com/chandeln16/fyers_optionchain_dashboard
cd fyers-option-chain
2. Install Dependencies

Bash
pip install -r requirements.txt
3. Run the Streamlit App

Bash
streamlit run app.py



🌐 How to Use the App
Step 1: Open the app in your browser (usually http://localhost:8501).

Step 2: Open the sidebar and enter your Fyers Client ID (e.g., XXXXXXX-100) and today's Access Token.

Step 3: Click on Connect to Fyers.

Step 4: Select your preferred Index and Expiry Date.

Step 5: Turn on Auto-Refresh to get live data every 5 seconds!

⚠️ Disclaimer
This dashboard is built for educational and analytical purposes only. Please do not use this solely for executing real-money trades. Always verify data with your broker's official terminal.

👨‍💻 Developer & Author
Narendra * Instagram: @chandeln16

X (Twitter): @chandeln16

Feel free to reach out for feedback or collaborations! If you find this project helpful, don't forget to ⭐ star the repository.
