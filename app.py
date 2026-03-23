from flask import Flask, render_template, jsonify, request
import pandas as pd
import os
from data_loader import get_processed_data, AIRLINE_NAMES, AIRPORT_CITIES
from model import FlightDelayModel

app = Flask(__name__)

flight_model = FlightDelayModel()
flight_data = None
analysis_data = None
model_metrics = None


def initialize_app():
    global flight_data, analysis_data, model_metrics

    #load real dataset
    flight_data = get_processed_data(
        filepath='data/flights.csv',
        cache_path='data/flights_processed.csv',
        sample_size=100000
    )

    #train model
    model_metrics = flight_model.train(flight_data)

    # Generate analysis
    analysis_data = flight_model.get_analysis_data(flight_data)

    print("\nDashboard ready at http://localhost:5000")

# build dynamic airline/airport maps from actual data

def get_airlines_from_data():
    if flight_data is None:
        return AIRLINE_NAMES
    airlines_in_data = flight_data['AIRLINE'].unique()
    return {code: AIRLINE_NAMES.get(code, code) for code in sorted(airlines_in_data)}


def get_airports_from_data():
    if flight_data is None:
        return AIRPORT_CITIES
    airports_in_data = flight_data['ORIGIN'].unique()
    return {code: AIRPORT_CITIES.get(code, code) for code in sorted(airports_in_data)}



@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analysis')
def get_analysis():
    return jsonify({
        'analysis': analysis_data,
        'airlines': get_airlines_from_data(),
        'airports': get_airports_from_data()
    })


@app.route('/api/metrics')
def get_metrics():
    return jsonify(model_metrics)


@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()

        airline = str(data.get('airline', 'AA'))
        origin = str(data.get('origin', 'ATL'))
        dep_hour = max(0, min(23, int(data.get('dep_hour', 12))))
        month = max(1, min(12, int(data.get('month', 6))))
        day_of_week = max(1, min(7, int(data.get('day_of_week', 3))))
        distance = max(50, min(5000, int(data.get('distance', 1000))))

        result = flight_model.predict(
            airline=airline,
            origin=origin,
            dep_hour=dep_hour,
            month=month,
            day_of_week=day_of_week,
            distance=distance
        )

        result['airline_name'] = AIRLINE_NAMES.get(airline, airline)
        result['airport_name'] = AIRPORT_CITIES.get(origin, origin)

        return jsonify(result)

    except Exception as e:
        print(f"Prediction error: {e}")
        return jsonify({'error': str(e)}), 400


@app.route('/api/airline-analysis/<airline_code>')
def airline_analysis(airline_code):
    if flight_data is None:
        return jsonify({'error': 'Data not loaded'}), 500

    df = flight_data[flight_data['AIRLINE'] == airline_code].copy()
    if len(df) == 0:
        return jsonify({'error': 'Airline not found'}), 404

    df['DELAYED'] = df['DELAYED'].fillna(0).astype(int)
    df['DEP_DELAY'] = df['DEP_DELAY'].fillna(0)

    month_names = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
                   5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
                   9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}

    monthly = df.groupby('MONTH').agg(
        total=('DELAYED', 'count'),
        delayed=('DELAYED', 'sum')
    ).reset_index()
    monthly['delay_rate'] = round(monthly['delayed'] / monthly['total'] * 100, 2)
    monthly['month_name'] = monthly['MONTH'].map(month_names)

    delayed_flights = df[df['DELAYED'] == 1]
    avg_delay = float(delayed_flights['DEP_DELAY'].mean()) if len(delayed_flights) > 0 else 0

    return jsonify({
        'airline_name': AIRLINE_NAMES.get(airline_code, airline_code),
        'total_flights': int(len(df)),
        'delayed_flights': int(df['DELAYED'].sum()),
        'delay_rate': round(float(df['DELAYED'].mean()) * 100, 2),
        'avg_delay': round(avg_delay, 1),
        'monthly': {
            'labels': monthly['month_name'].tolist(),
            'delay_rates': monthly['delay_rate'].tolist()
        }
    })


if __name__ == '__main__':
    initialize_app()
    app.run(debug=True, port=5000)