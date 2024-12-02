from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
import pickle
import json
import numpy as np
from google.cloud import firestore
from google.oauth2.service_account import Credentials

# Setup Flask app
app = Flask(__name__)

# Load the Isolation Forest model from PKL file
with open('isolation_forest_model.pkl', 'rb') as model_file:
    model = pickle.load(model_file)

#bikin json file nya dulu ygy
with open('recarticle.json', 'r') as file:
    data_article = json.load(file)

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

def generate_chart_data(transactions):
    # Initialize chart data
    category_distribution = {}
    income_vs_expenses = {'income': 0, 'expenses': 0}
    spending_trends = {}

    for transaction in transactions:
        trans_data = transaction.to_dict()
        if 'amount' in trans_data and 'type' in trans_data and 'category' in trans_data:
            amount = trans_data['amount']
            category = trans_data['category']
            trans_type = trans_data['type']
            date = trans_data.get('date', 'unknown')[:10]  # Extract date as YYYY-MM-DD

            # Update income vs. expenses
            if trans_type == 'income':
                income_vs_expenses['income'] += amount
            elif trans_type == 'expenses':
                income_vs_expenses['expenses'] += amount

                # Update category distribution
                if category not in category_distribution:
                    category_distribution[category] = 0
                category_distribution[category] += amount

                # Update spending trends
                if date not in spending_trends:
                    spending_trends[date] = 0
                spending_trends[date] += amount

    return {
        'categoryDistribution': category_distribution,
        'incomeVsExpenses': income_vs_expenses,
        'spendingTrends': spending_trends
    }

def generate_financial_advice(chart_data):
    advice = []
    income = chart_data['incomeVsExpenses']['income']
    expenses = chart_data['incomeVsExpenses']['expenses']
    savings = income - expenses

    # Savings advice
    if savings < (income * 0.2):  # Less than 20% savings
        advice.append("Consider increasing your savings by reducing non-essential expenses.")

    # High spending categories advice
    for category, total in chart_data['categoryDistribution'].items():
        if total > (expenses * 0.3):  # More than 30% of expenses in one category
            advice.append(f"You are spending a lot on {category}. Try setting a budget limit.")

    # General advice
    if expenses > income:
        advice.append("Your expenses exceed your income. Consider reviewing your spending habits.")

    return advice

# @app.route('/initialize_balance', methods=['POST'])
# def initialize_balance():
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

# @app.route('/add_transaction', methods=['POST'])
# def add_transaction():
#     try:
#         # Input transaction data (income or expense)
#         data = request.json
#         user_id = data.get('userId')
#         transaction_type = data.get('transactionType')  # 'income' or 'expense'
#         amount = data.get('amount')
#         category = data.get('category')
        
#         # Validate the inputs
#         if not user_id or not transaction_type or amount is None or not category:
#             return jsonify({"error": "Missing required fields"}), 400
        
#         if transaction_type not in ['income', 'expense']:
#             return jsonify({"error": "Invalid transaction type"}), 400

#         # Store the transaction in Firestore
#         transaction_ref = db.collection('users').document(user_id).collection('transactions').document()
#         transaction_ref.set({
#             'transactionType': transaction_type,
#             'amount': amount,
#             'category': category,
#             'timestamp': firestore.SERVER_TIMESTAMP
#         })
        
#         # Handle anomaly detection based on new transaction
#         transactions_ref = db.collection('users').document(user_id).collection('transactions')
#         expenses_list = []
        
#         # Fetch and accumulate expenses
#         month_transactions = transactions_ref.stream()
#         for transaction in month_transactions:
#             trans_data = transaction.to_dict()
#             if trans_data['transactionType'] == 'expense':
#                 expenses_list.append(trans_data['amount'])

#         # Detect anomalies in expenses
#         anomalies = detect_anomalies(expenses_list)
        
#         # Prepare response
#         return jsonify({
#             'message': 'Transaction added successfully',
#             'anomalies': anomalies
#         }), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@app.route('/analytics/<userId>/<month>', methods=['GET'])
def get_monthly_analytics(userId, month):
    try:
        transactions_ref = db.collection('users').document(userId).collection('transactions').document(month).collection('records')
        month_transactions = list(transactions_ref.stream())

        # Generate analytics data
        chart_data = generate_chart_data(month_transactions)

        # Detect anomalies
        expense_amounts = [
            trans.to_dict().get('amount', 0)
            for trans in month_transactions
            if trans.to_dict().get('type', '').lower() == 'expenses'
        ]
        print(f"Expenses detected for anomaly detection: {expense_amounts}")
        anomalies = detect_anomalies(expense_amounts)

        # Generate financial advice
        financial_advice = generate_financial_advice(chart_data)

        # Prepare response
        monthly_analytics = {
            'userId': userId,
            'month': month,
            'chartData': chart_data,
            'anomalies': anomalies,
            'financialAdvice': financial_advice
        }

        # Save to Firestore (optional)
        # db.collection('users').document(userId).collection('transactions').document(month).collection('analysis').document('result').set(monthly_analytics)
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
    app.run(debug=True, host="0.0.0.0", port=5000)
