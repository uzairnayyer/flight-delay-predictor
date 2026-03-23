import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score, confusion_matrix,
    precision_score, recall_score, f1_score
)
import warnings
warnings.filterwarnings('ignore')


class FlightDelayModel:

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = []
        self.metrics = {}
        self.is_trained = False

        # Store known categories for validation
        self.known_airlines = []
        self.known_airports = []

    def clean_data(self, df):
        """        
        this handles:
        -missing values
        -invalid data types
        -outlier departure delays
        """
        df_clean = df.copy()

        numerical_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
        for col in numerical_cols:
            if df_clean[col].isnull().any():
                median_val = df_clean[col].median()
                df_clean[col] = df_clean[col].fillna(median_val)
                null_count = df[col].isnull().sum()
                print(f"  Filled {null_count} missing values in {col} with median ({median_val:.1f})")

        df_clean['DELAYED'] = df_clean['DELAYED'].fillna(0).astype(int)
        df_clean['DEP_HOUR'] = df_clean['DEP_HOUR'].fillna(12).astype(int).clip(0, 23)
        df_clean['MONTH'] = df_clean['MONTH'].fillna(6).astype(int).clip(1, 12)
        df_clean['DAY_OF_WEEK'] = df_clean['DAY_OF_WEEK'].fillna(4).astype(int).clip(1, 7)
        df_clean['DISTANCE'] = df_clean['DISTANCE'].fillna(1000).clip(lower=1)

        # extreme delay values (some flights show 1000+ min delays)
        # but this helps the model not be skewed by extreme outliers
        if 'DEP_DELAY' in df_clean.columns:
            before_cap = (df_clean['DEP_DELAY'] > 600).sum()
            df_clean['DEP_DELAY'] = df_clean['DEP_DELAY'].clip(upper=600)
            if before_cap > 0:
                print(f"  Capped {before_cap} extreme delay values at 600 minutes")

        # Store known categories
        self.known_airlines = df_clean['AIRLINE'].unique().tolist()
        self.known_airports = df_clean['ORIGIN'].unique().tolist()

        remaining_nan = df_clean.select_dtypes(include=[np.number]).isnull().sum().sum()
        print(f"  Clean dataset: {df_clean.shape[0]:,} rows, {remaining_nan} remaining NaN")
        return df_clean

    def engineer_features(self, df):
        """
        create new features from the real flight data.
        
        features created:
        - TIME_PERIOD: early morning/morning/afternoon/evening/night
        - IS_WEEKEND: saturday or Sunday flag
        - DIST_CATEGORY: short/medium/long/very long haul
        - SEASON: winter/spring/summer/fall
        """
        print("Engineering features...")
        df_feat = df.copy()

        # Time of day category
        def get_time_period(hour):
            try:
                hour = int(hour)
            except (ValueError, TypeError):
                return 1
            if 5 <= hour <= 8:
                return 0  # Early Morning
            elif 9 <= hour <= 12:
                return 1  # Morning
            elif 13 <= hour <= 16:
                return 2  # Afternoon
            elif 17 <= hour <= 20:
                return 3  # Evening
            else:
                return 4  # Night

        df_feat['TIME_PERIOD'] = df_feat['DEP_HOUR'].apply(get_time_period).astype(int)

        # Is weekend flag
        df_feat['IS_WEEKEND'] = (df_feat['DAY_OF_WEEK'] >= 6).astype(int)

        # Distance category using np.select (avoids pd.cut NaN issues)
        conditions = [
            df_feat['DISTANCE'] <= 500,
            (df_feat['DISTANCE'] > 500) & (df_feat['DISTANCE'] <= 1500),
            (df_feat['DISTANCE'] > 1500) & (df_feat['DISTANCE'] <= 3000),
            df_feat['DISTANCE'] > 3000
        ]
        choices = [0, 1, 2, 3]
        df_feat['DIST_CATEGORY'] = np.select(conditions, choices, default=1).astype(int)

        # Season from month
        def get_season(month):
            try:
                month = int(month)
            except (ValueError, TypeError):
                return 2
            if month in [12, 1, 2]:
                return 0  # Winter
            elif month in [3, 4, 5]:
                return 1  # Spring
            elif month in [6, 7, 8]:
                return 2  # Summer
            else:
                return 3  # Fall

        df_feat['SEASON'] = df_feat['MONTH'].apply(get_season).astype(int)

        print(f"  Created features: TIME_PERIOD, IS_WEEKEND, DIST_CATEGORY, SEASON")

        # Safety: fill any remaining NaN
        nan_count = df_feat.select_dtypes(include=[np.number]).isnull().sum().sum()
        if nan_count > 0:
            df_feat = df_feat.fillna(0)
            print(f"  Filled {nan_count} remaining NaN values with 0")

        return df_feat

    def prepare_features(self, df, fit_encoders=True):
        categorical_features = ['AIRLINE', 'ORIGIN']
        df_model = df.copy()

        for col in categorical_features:
            if fit_encoders:
                le = LabelEncoder()
                df_model[col + '_ENCODED'] = le.fit_transform(df_model[col].astype(str))
                self.label_encoders[col] = le
            else:
                le = self.label_encoders[col]
                df_model[col + '_ENCODED'] = df_model[col].astype(str).apply(
                    lambda x: le.transform([x])[0] if x in le.classes_ else 0
                )

        self.feature_columns = [
            'AIRLINE_ENCODED', 'ORIGIN_ENCODED', 'DEP_HOUR',
            'MONTH', 'DAY_OF_WEEK', 'DISTANCE', 'TIME_PERIOD',
            'IS_WEEKEND', 'DIST_CATEGORY', 'SEASON',
            'TAXI_OUT', 'CRS_ELAPSED_TIME'
        ]

        X = df_model[self.feature_columns].values.astype(float)

        # Final NaN safety net
        if np.isnan(X).any():
            nan_count = np.isnan(X).sum()
            print(f"  Replacing {nan_count} NaN in feature matrix")
            X = np.nan_to_num(X, nan=0.0)

        return X

    def train(self, df):
        # Clean
        df_clean = self.clean_data(df)

        #feature engineering
        df_feat = self.engineer_features(df_clean)

        #prepare feature matrix
        X = self.prepare_features(df_feat, fit_encoders=True)
        y = df_feat['DELAYED'].values.astype(int)

        #validate
        assert not np.isnan(X).any(), "Feature matrix contains NaN!"
        assert not np.isnan(y).any(), "Target variable contains NaN!"
        print(f"\ndata validation passed")
        print(f"  Feature matrix shape: {X.shape}")
        print(f"  Class distribution: On-time={np.sum(y==0):,}, Delayed={np.sum(y==1):,}")

        #split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        print(f"  Training: {len(X_train):,} | Testing: {len(X_test):,}")

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        X_train_scaled = np.nan_to_num(X_train_scaled, nan=0.0)
        X_test_scaled = np.nan_to_num(X_test_scaled, nan=0.0)

        #train
        print("\nTraining Logistic Regression...")
        self.model = LogisticRegression(
            max_iter=1000,
            random_state=42,
            C=1.0,
            solver='lbfgs'
        )
        self.model.fit(X_train_scaled, y_train)
        print("Model trained successfully!")

        y_pred = self.model.predict(X_test_scaled)

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        cm = confusion_matrix(y_test, y_pred)

        self.metrics = {
            'accuracy': round(accuracy * 100, 2),
            'precision': round(precision * 100, 2),
            'recall': round(recall * 100, 2),
            'f1_score': round(f1 * 100, 2),
            'confusion_matrix': cm.tolist(),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'total_features': len(self.feature_columns),
            'feature_names': self.feature_columns,
            'dataset_info': {
                'name': '2015 Flight Delays and Cancellations',
                'source': 'U.S. Department of Transportation (via Kaggle)',
                'total_records_used': len(df_feat),
                'airlines_count': df_feat['AIRLINE'].nunique(),
                'airports_count': df_feat['ORIGIN'].nunique(),
            }
        }

        feature_importance = dict(zip(
            self.feature_columns,
            [round(float(c), 4) for c in self.model.coef_[0]]
        ))
        self.metrics['feature_importance'] = feature_importance

        print(f"\n--- Model Performance on Real Data ---")
        print(f"Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
        print(f"Precision: {precision:.4f}")
        print(f"Recall:    {recall:.4f}")
        print(f"F1 Score:  {f1:.4f}")
        print(f"\nConfusion Matrix:")
        print(f"  TN={cm[0][0]:,}  FP={cm[0][1]:,}")
        print(f"  FN={cm[1][0]:,}  TP={cm[1][1]:,}")

        self.is_trained = True
        print("\nTraining complete!")
        return self.metrics

    def predict(self, airline, origin, dep_hour, month, day_of_week,
                distance, taxi_out=16, elapsed_time=None):
        if not self.is_trained:
            return {'error': 'Model not trained yet'}

        dep_hour = int(dep_hour)
        month = int(month)
        day_of_week = int(day_of_week)
        distance = int(distance)
        taxi_out = int(taxi_out)

        # Derived features
        if 5 <= dep_hour <= 8:
            time_period = 0
        elif 9 <= dep_hour <= 12:
            time_period = 1
        elif 13 <= dep_hour <= 16:
            time_period = 2
        elif 17 <= dep_hour <= 20:
            time_period = 3
        else:
            time_period = 4

        is_weekend = 1 if day_of_week >= 6 else 0

        if distance <= 500:
            dist_category = 0
        elif distance <= 1500:
            dist_category = 1
        elif distance <= 3000:
            dist_category = 2
        else:
            dist_category = 3

        if month in [12, 1, 2]:
            season = 0
        elif month in [3, 4, 5]:
            season = 1
        elif month in [6, 7, 8]:
            season = 2
        else:
            season = 3

        if elapsed_time is None:
            elapsed_time = int(distance / 8) + 35

        try:
            airline_encoded = self.label_encoders['AIRLINE'].transform([airline])[0]
        except (ValueError, KeyError):
            airline_encoded = 0

        try:
            origin_encoded = self.label_encoders['ORIGIN'].transform([origin])[0]
        except (ValueError, KeyError):
            origin_encoded = 0

        features = np.array([[
            float(airline_encoded), float(origin_encoded), float(dep_hour),
            float(month), float(day_of_week), float(distance), float(time_period),
            float(is_weekend), float(dist_category), float(season),
            float(taxi_out), float(elapsed_time)
        ]])

        features = np.nan_to_num(features, nan=0.0)
        features_scaled = self.scaler.transform(features)
        features_scaled = np.nan_to_num(features_scaled, nan=0.0)

        prediction = self.model.predict(features_scaled)[0]
        probability = self.model.predict_proba(features_scaled)[0]

        return {
            'delayed': bool(prediction),
            'probability_delayed': round(float(probability[1]) * 100, 2),
            'probability_on_time': round(float(probability[0]) * 100, 2),
            'confidence': round(float(max(probability)) * 100, 2),
        }

    def get_analysis_data(self, df):
        """Generate aggregated analysis data for the dashboard charts."""
        df_clean = self.clean_data(df)

        #by airline
        airline_delays = df_clean.groupby('AIRLINE_NAME').agg(
            total_flights=('DELAYED', 'count'),
            delayed_flights=('DELAYED', 'sum'),
            avg_delay=('DEP_DELAY', 'mean')
        ).reset_index()
        airline_delays['delay_rate'] = round(
            airline_delays['delayed_flights'] / airline_delays['total_flights'] * 100, 2
        )
        airline_delays = airline_delays.sort_values('delay_rate', ascending=True)

        #by airport
        airport_delays = df_clean.groupby(['ORIGIN', 'ORIGIN_CITY']).agg(
            total_flights=('DELAYED', 'count'),
            delayed_flights=('DELAYED', 'sum'),
            avg_delay=('DEP_DELAY', 'mean')
        ).reset_index()
        airport_delays['delay_rate'] = round(
            airport_delays['delayed_flights'] / airport_delays['total_flights'] * 100, 2
        )
        airport_delays = airport_delays.sort_values('delay_rate', ascending=True)

        #by month
        month_names = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
            5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
            9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
        }
        monthly_delays = df_clean.groupby('MONTH').agg(
            total_flights=('DELAYED', 'count'),
            delayed_flights=('DELAYED', 'sum'),
            avg_delay=('DEP_DELAY', 'mean')
        ).reset_index()
        monthly_delays['delay_rate'] = round(
            monthly_delays['delayed_flights'] / monthly_delays['total_flights'] * 100, 2
        )
        monthly_delays['month_name'] = monthly_delays['MONTH'].map(month_names)

        #by hour
        hourly_delays = df_clean.groupby('DEP_HOUR').agg(
            total_flights=('DELAYED', 'count'),
            delayed_flights=('DELAYED', 'sum'),
            avg_delay=('DEP_DELAY', 'mean')
        ).reset_index()
        hourly_delays['delay_rate'] = round(
            hourly_delays['delayed_flights'] / hourly_delays['total_flights'] * 100, 2
        )

        #by day of week
        day_names = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu',
                     5: 'Fri', 6: 'Sat', 7: 'Sun'}
        daily_delays = df_clean.groupby('DAY_OF_WEEK').agg(
            total_flights=('DELAYED', 'count'),
            delayed_flights=('DELAYED', 'sum')
        ).reset_index()
        daily_delays['delay_rate'] = round(
            daily_delays['delayed_flights'] / daily_delays['total_flights'] * 100, 2
        )
        daily_delays['day_name'] = daily_delays['DAY_OF_WEEK'].map(day_names)

        total_flights = len(df_clean)
        total_delayed = int(df_clean['DELAYED'].sum())
        delayed_only = df_clean[df_clean['DELAYED'] == 1]['DEP_DELAY']
        avg_delay = float(delayed_only.mean()) if len(delayed_only) > 0 else 0

        return {
            'overall': {
                'total_flights': int(total_flights),
                'total_delayed': int(total_delayed),
                'delay_rate': round(total_delayed / total_flights * 100, 2),
                'avg_delay_minutes': round(avg_delay, 1)
            },
            'by_airline': {
                'labels': airline_delays['AIRLINE_NAME'].tolist(),
                'delay_rates': airline_delays['delay_rate'].tolist(),
                'total_flights': airline_delays['total_flights'].tolist(),
                'delayed_flights': airline_delays['delayed_flights'].tolist()
            },
            'by_airport': {
                'labels': [f"{row['ORIGIN']} ({row['ORIGIN_CITY']})"
                           for _, row in airport_delays.iterrows()],
                'codes': airport_delays['ORIGIN'].tolist(),
                'delay_rates': airport_delays['delay_rate'].tolist(),
                'total_flights': airport_delays['total_flights'].tolist()
            },
            'by_month': {
                'labels': monthly_delays['month_name'].tolist(),
                'delay_rates': monthly_delays['delay_rate'].tolist(),
                'total_flights': monthly_delays['total_flights'].tolist(),
                'avg_delay': [round(x, 1) for x in monthly_delays['avg_delay'].tolist()]
            },
            'by_hour': {
                'labels': hourly_delays['DEP_HOUR'].tolist(),
                'delay_rates': hourly_delays['delay_rate'].tolist(),
                'total_flights': hourly_delays['total_flights'].tolist()
            },
            'by_day': {
                'labels': daily_delays['day_name'].tolist(),
                'delay_rates': daily_delays['delay_rate'].tolist()
            }
        }