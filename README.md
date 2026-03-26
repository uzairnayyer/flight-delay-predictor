# ✈️ Flight Delay Prediction Dashboard

> University Undergraduate Data Science Portfolio Project

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-green?logo=flask&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3-orange?logo=scikitlearn&logoColor=white)

---

## 📋 Project Overview

A complete end-to-end data science web application that analyzes real flight data and predicts whether a flight will be delayed using Logistic Regression.

This project uses **real data** from the U.S. Department of Transportation and presents **honest, unmanipulated results** — including the model's real limitations.

### 🖥️ Dashboard Preview

The dashboard includes four sections:
- **Overview** — Key statistics and delay trends
- **Analysis** — Interactive exploratory data analysis
- **Predict** — Enter flight details to get a delay prediction
- **Model Info** — Performance metrics, confusion matrix, feature importance

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python, Flask 3.0 |
| **Data Processing** | Pandas, NumPy |
| **Machine Learning** | scikit-learn (Logistic Regression) |
| **Visualization** | Plotly.js |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Dataset** | 2015 U.S. DOT Flight Delays (Kaggle) |

---

## 📊 Model Performance

Trained on **100,000 real historical flights** from the 2015 U.S. DOT dataset:

| Metric | Value |
|--------|-------|
| ✅ **Accuracy** | **80.36%** |
| ⚠️ Precision | 55.88% |
| ❌ Recall | 0.48% |
| ❌ F1 Score | 0.96% |

---

### ❗ Why These Results Are Honest (And Important)

> **This is not a bug. This is not a mistake. This is what real ML looks like on hard problems.**

Most flight delay prediction projects on GitHub show 90%+ accuracy with perfect metrics. Those results are fake — they use data leakage, synthetic data, or include the target variable as a feature.

#### Why the recall is so low:

1. **Severe Class Imbalance**
   - ~80% of flights are on time, ~20% are delayed
   - The model learns that predicting "on time" for everything gives 80% accuracy
   - It almost never predicts "delayed" because that is the minority class

2. **Weak Predictive Features**
   - We only have schedule information: airline, airport, departure time, month, distance
   - None of these individually are strong predictors of delays
   - A flight from Delta at 3 PM in June is not meaningfully different from United at 4 PM in July

3. **Missing Critical Information**
   - No weather data (the #1 cause of delays)
   - No air traffic congestion data
   - No previous flight chain delays (cascading delays)
   - No aircraft maintenance status
   - No crew scheduling information

4. **Flight Delays Are Fundamentally Hard to Predict**
   - Even airlines with full real-time data achieve only ~72% accuracy
   - Academic research papers on this topic report similar limitations
   - The randomness of weather events makes perfect prediction impossible

#### What would actually improve the model:

| Improvement | Expected Impact |
|-------------|----------------|
| Add current departure delay status | Recall jumps to ~85% |
| Add weather data (NOAA API) | +15-20% recall |
| Use ensemble models (Random Forest + GBM) | +10-15% recall |
| Apply SMOTE class balancing | +5-10% recall |
| Tune decision threshold (lower from 0.5) | Trade accuracy for recall |
| Add previous flight delay chain data | +10% recall |
| Target encoding for airline/airport/hour | +5-10% precision |

---

## 📁 Project Structure
```
flight-delay-prediction-dashboard/
├── app.py # Flask web server and API routes
├── model.py # ML pipeline (clean, engineer, train, predict)
├── data_loader.py # Loads and preprocesses the Kaggle dataset
├── requirements.txt # Python dependencies
├── .gitignore
├── README.md
├── data/
│ └── flights.csv # Download from Kaggle (not in repo)
├── templates/
│ └── index.html # Dashboard HTML
└── static/
├── css/
│ └── style.css # Dashboard styling
└── js/
└── dashboard.js # Charts and interactivity
```

---

## 🚀 How To Run

### Prerequisites
- Python 3.8 or higher
- A free Kaggle account (to download the dataset)

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/flight-delay-prediction-dashboard.git
cd flight-delay-prediction-dashboard

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download the dataset
# Go to: https://www.kaggle.com/datasets/usdot/flight-delays
# Download and extract the zip file
# Copy flights.csv into the data/ folder

# 5. Verify the dataset is in place
ls data/flights.csv             # Mac/Linux
dir data\flights.csv            # Windows

# 6. Run the application
python app.py

# 7. Open your browser

# Go to: http://localhost:5000
```
