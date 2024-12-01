from flask import Flask, jsonify, request
import pickle
import numpy as np
from google.cloud import firestore
from google.oauth2.service_account import Credentials

# Setup Flask app
app = Flask(__name__)

# Load the Isolation Forest model from PKL file
with open('Ez_money.pkl', 'rb') as model_file:
    model = pickle.load(model_file)

# Google Cloud Firestore setup
credentials = Credentials.from_service_account_file('./firestore-admin.json')
db = firestore.Client(credentials=credentials, project='capstone-ezmoney-service-app')

# Array to hold all analysis results
all_analytics = []

# Function to detect anomalies using the loaded model
def detect_anomalies(expenses: list):
    if not expenses:  # If the expenses list is empty
        return []  # Return an empty list (no anomalies)

    data = np.array(expenses).reshape(-1, 1)
    
    # Ensure that model receives at least one data point
    if data.shape[0] == 0:
        return []
    
    predictions = model.predict(data)
    
    # -1 means anomaly, 1 means normal
    anomalies = [expense for expense, prediction in zip(expenses, predictions) if prediction == -1]
    return anomalies

@app.route('/initialize_balance', methods=['POST'])
def initialize_balance():
    try:
        # Input initial income and savings mode
        data = request.json
        total_income = data.get('totalIncome', 0)
        saving_percentage = data.get('savingPercentage', 30)

        # Calculate savings and balance
        if saving_percentage == 30:
            savings = total_income * 0.30
        elif saving_percentage == 50:
            savings = total_income * 0.50
        elif saving_percentage == 80:
            savings = total_income * 0.80
        else:
            savings = total_income * 0.30  # Default to 30% saving

        balance = total_income - savings

        # Return the result
        return jsonify({
            'totalIncome': total_income,
            'savings': savings,
            'balance': balance
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    try:
        # Input transaction data (income or expense)
        data = request.json
        user_id = data.get('userId')
        transaction_type = data.get('transactionType')  # 'income' or 'expense'
        amount = data.get('amount')
        category = data.get('category')
        
        # Validate the inputs
        if not user_id or not transaction_type or amount is None or not category:
            return jsonify({"error": "Missing required fields"}), 400
        
        if transaction_type not in ['income', 'expense']:
            return jsonify({"error": "Invalid transaction type"}), 400

        # Store the transaction in Firestore
        transaction_ref = db.collection('users').document(user_id).collection('transactions').document()
        transaction_ref.set({
            'transactionType': transaction_type,
            'amount': amount,
            'category': category,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        # Handle anomaly detection based on new transaction
        transactions_ref = db.collection('users').document(user_id).collection('transactions')
        expenses_list = []
        
        # Fetch and accumulate expenses
        month_transactions = transactions_ref.stream()
        for transaction in month_transactions:
            trans_data = transaction.to_dict()
            if trans_data['transactionType'] == 'expense':
                expenses_list.append(trans_data['amount'])

        # Detect anomalies in expenses
        anomalies = detect_anomalies(expenses_list)
        
        # Prepare response
        return jsonify({
            'message': 'Transaction added successfully',
            'anomalies': anomalies
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analytics/<userId>/<month>', methods=['GET'])
def get_monthly_analytics(userId, month):
    try:
        # Fetch monthly transaction data from Firestore
        transactions_ref = db.collection('users').document(userId).collection('transactions')
        month_transactions = transactions_ref.where('month', '==', month).stream()

        # Initialize variables to calculate total income and expenses
        total_income = 0.0
        total_expenses = 0.0
        expenses_list = []
        
        for transaction in month_transactions:
            trans_data = transaction.to_dict()
            # Calculate total income and expenses
            if 'amount' in trans_data:
                if trans_data['transactionType'] == 'income':
                    total_income += trans_data['amount']
                elif trans_data['transactionType'] == 'expense':
                    total_expenses += trans_data['amount']
                    expenses_list.append(trans_data['amount'])

        # Detect anomalies in the expenses, but only if there are expenses data
        anomalies = detect_anomalies(expenses_list)

        # Prepare the monthly analytics data
        monthly_analytics = {
            'userId': userId,
            'month': month,
            'totalIncome': total_income,
            'totalExpenses': total_expenses,
            'balance': total_income - total_expenses,
            'anomalies': anomalies
        }

        # Add the result to the array (instead of saving directly to Firestore)
        all_analytics.append(monthly_analytics)

        # Optionally: Return the analytics data for this request
        return jsonify(monthly_analytics), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/save_all_analytics', methods=['POST'])
def save_all_analytics():
    try:
        # Save all analytics results in Firestore at once
        for analytics in all_analytics:
            user_ref = db.collection('users').document(analytics['userId']).collection('transactions')
            month_analytics_ref = user_ref.document(analytics['month']).collection('analysis').document('result')
            month_analytics_ref.set(analytics)

        # Clear the array after saving
        all_analytics.clear()

        return jsonify({"message": "All analytics have been saved to Firestore"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
