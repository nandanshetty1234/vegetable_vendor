from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum, F
from .models import VegetableSale, DailySummary, VegetableReport,ReportSummary
from datetime import date
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import numpy as np
import urllib, base64
from io import BytesIO





def vegetable_list(request):
    """Display all vegetables for the selected date, including default ones."""
    selected_date = request.session.get('selected_date', str(date.today()))
    selected_date = date.fromisoformat(selected_date)

    default_vegetables = ["Onion", "Tomato", "Potato", "Carrot", "Brinjal"]

    # Fetch existing vegetables for the selected date
    existing_vegetables = VegetableSale.objects.filter(date=selected_date)
    existing_vegetable_names = existing_vegetables.values_list('vegetable', flat=True)

    # Add missing default vegetables
    missing_vegetables = [veg for veg in default_vegetables if veg not in existing_vegetable_names]
    VegetableSale.objects.bulk_create(
        [VegetableSale(vegetable=veg, date=selected_date, quantity=None, purchase_price=None, selling_price=None) for veg in missing_vegetables]
    )

    # Fetch updated vegetables list
    vegetables = VegetableSale.objects.filter(date=selected_date)

    return render(request, 'sales/vegetable_list.html', {
        'vegetables': vegetables,
        'selected_date': selected_date
    })


def set_date(request):
    """Save the selected date in session and reload data."""
    if request.method == "POST":
        selected_date = request.POST.get("date")
        if selected_date:
            request.session['selected_date'] = selected_date
            return JsonResponse({"success": True, "message": f"Date set to {selected_date}"})
    return JsonResponse({"success": False, "message": "Invalid date selection."})


def add_vegetable(request):
    """Add a new vegetable for the selected date."""
    if request.method == "POST":
        veg_name = request.POST.get("vegetable_name", "").strip()
        if not veg_name:
            return JsonResponse({"success": False, "message": "Vegetable name is required."})

        selected_date = request.session.get("selected_date", str(date.today()))
        selected_date = date.fromisoformat(selected_date)

        vegetable, created = VegetableSale.objects.get_or_create(
            vegetable=veg_name, date=selected_date,
            defaults={"quantity": None, "purchase_price": None, "selling_price": None}
        )

        return JsonResponse({
            "success": True,
            "message": "Vegetable added successfully." if created else "Vegetable already exists.",
            "vegetable": {
                "name": vegetable.vegetable,
                "quantity": vegetable.quantity,
                "purchase_price": vegetable.purchase_price,
                "selling_price": vegetable.selling_price
            }
        })

    return JsonResponse({"success": False, "message": "Invalid request method."})


def delete_vegetable(request):
    """Delete a vegetable for the selected date."""
    if request.method == "POST":
        vegetable_name = request.POST.get("vegetable_name")
        selected_date = request.session.get("selected_date", str(date.today()))
        selected_date = date.fromisoformat(selected_date)

        deleted_count, _ = VegetableSale.objects.filter(vegetable=vegetable_name, date=selected_date).delete()

        if deleted_count > 0:
            return JsonResponse({"success": True, "message": f"Deleted {deleted_count} record(s)."})
        return JsonResponse({"success": False, "message": "Vegetable not found for the selected date."})

    return JsonResponse({"success": False, "message": "Invalid request!"})


def calculate_totals(request):
    selected_date = request.session.get('selected_date', str(date.today()))
    selected_date = date.fromisoformat(selected_date)

    totals = VegetableSale.objects.filter(date=selected_date).aggregate(
        total_purchase=Sum(F('quantity') * F('purchase_price')),
        total_selling=Sum(F('quantity') * F('selling_price'))
    )

    total_purchase = totals['total_purchase'] or 0
    total_selling = totals['total_selling'] or 0
    profit = max(0, total_selling - total_purchase)
    loss = max(0, total_purchase - total_selling)

    # Save or update the daily summary
    DailySummary.objects.update_or_create(
        date=selected_date,
        defaults={
            'total_purchase_price': total_purchase,
            'total_selling_price': total_selling,
            'total_profit': profit,
            'total_loss': loss
        }
    )

    return JsonResponse({
        'success': True,
        'total_purchase_price': total_purchase,
        'total_selling_price': total_selling,
        'profit': profit,
        'loss': loss
    })


def save_data(request):
    """Save updated vegetable data for the selected date."""
    if request.method == "POST":
        selected_date = request.session.get('selected_date', str(date.today()))
        selected_date = date.fromisoformat(selected_date)

        updated_vegetables = []
        for key, value in request.POST.items():
            if key.startswith("quantity_"):
                veg_id = key.split("_")[1]
                try:
                    vegetable = VegetableSale.objects.get(id=veg_id, date=selected_date)
                    vegetable.quantity = float(value)
                    vegetable.purchase_price = float(request.POST.get(f"purchase_price_{veg_id}", 0))
                    vegetable.selling_price = float(request.POST.get(f"selling_price_{veg_id}", 0))
                    updated_vegetables.append(vegetable)
                except VegetableSale.DoesNotExist:
                    continue

        if updated_vegetables:
            VegetableSale.objects.bulk_update(updated_vegetables, ["quantity", "purchase_price", "selling_price"])

        return JsonResponse({"success": True, "message": "Data saved successfully!"})

    return JsonResponse({"success": False, "message": "Invalid request method."})





def report_page(request):
    selected_date = request.GET.get('date') or request.POST.get('selected_date')
    show_chart = 'show_chart' in request.POST  # Detect if user clicked "Quantity Analysis"
    data = []
    message = ""
    summary = None
    chart_url = None

    if selected_date:
        entries = VegetableSale.objects.filter(date=selected_date)
        filtered_entries = entries.filter(quantity__gt=0) | entries.filter(purchase_price__gt=0) | entries.filter(selling_price__gt=0)

        if not filtered_entries.exists():
            message = "No vegetables were purchased on this date."
        else:
            # Clear previous report
            VegetableReport.objects.filter(date=selected_date).delete()

            total_purchase_sum = 0
            total_selling_sum = 0
            total_profit = 0
            total_loss = 0

            for entry in filtered_entries:
                quantity = entry.quantity or 0
                purchase_price = entry.purchase_price or 0
                selling_price = entry.selling_price or 0

                total_purchase = purchase_price * quantity
                total_selling = selling_price * quantity
                profit = max(total_selling - total_purchase, 0)
                loss = max(total_purchase - total_selling, 0)

                total_purchase_sum += total_purchase
                total_selling_sum += total_selling
                total_profit += profit
                total_loss += loss

                VegetableReport.objects.create(
                    date=selected_date,
                    vegetable=entry.vegetable,
                    quantity=quantity,
                    purchase_price=purchase_price,
                    selling_price=selling_price,
                    total_purchase=total_purchase,
                    total_selling=total_selling,
                    profit=profit,
                    loss=loss
                )

                data.append({
                    'vegetable': entry.vegetable,
                    'quantity': quantity,
                    'purchase_price': purchase_price,
                    'selling_price': selling_price,
                    'total_purchase': total_purchase,
                    'total_selling': total_selling,
                    'profit': profit,
                    'loss': loss,
                })

            summary, created = ReportSummary.objects.update_or_create(
                date=selected_date,
                defaults={
                    'total_purchase': total_purchase_sum,
                    'total_selling': total_selling_sum,
                    'profit': total_profit,
                    'loss': total_loss
                }
            )

            # ✅ Only generate chart if requested441
            if show_chart and data:
                vegetables = [item['vegetable'] for item in data]
                quantities = [item['quantity'] for item in data]
                base_colors = ['lightcoral', 'gold', 'lightsalmon', 'plum', 'skyblue', 'lightgreen', 'khaki', 'lightpink', 'peachpuff', 'aquamarine']
                colors = [base_colors[i % len(base_colors)] for i in range(len(vegetables))]

                plt.figure(figsize=(8,4))
                plt.bar(vegetables, quantities, color=colors,width=0.5)
                plt.xlabel('Vegetables')
                plt.ylabel('Quantity')
                plt.title(f'Quantity Analysis for {selected_date}')
                plt.xticks(rotation=45)
                plt.tight_layout()

                buffer = BytesIO()
                plt.savefig(buffer, format='png')
                buffer.seek(0)
                image_png = buffer.getvalue()
                buffer.close()
                chart_url = 'data:image/png;base64,' + base64.b64encode(image_png).decode('utf-8')
                plt.close()

    return render(request, 'sales/report.html', {
        'data': data,
        'selected_date': selected_date,
        'message': message,
        'summary': summary,
        'chart_url': chart_url,
    })

def price_chart(request):
    selected_date = request.GET.get('date')

    if not selected_date:
        return JsonResponse({'error': 'Date not provided'}, status=400)

    data = VegetableSale.objects.filter(date=selected_date)

    if not data.exists():
        return JsonResponse({'error': 'No data found for selected date'}, status=404)

    vegetables = [veg.vegetable for veg in data]
    purchase_prices = [veg.purchase_price for veg in data]
    selling_prices = [veg.selling_price for veg in data]

    # Create a line chart
    plt.figure(figsize=(10, 5))
    plt.plot(vegetables, purchase_prices, marker='o', label='Purchase Price', color='green')
    plt.plot(vegetables, selling_prices, marker='o', label='Selling Price', color='orange')
    plt.title(f'Price Analysis for {selected_date}')
    plt.xlabel('Vegetables')
    plt.ylabel('Price (per kg)')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()  # Important to close the plot to free memory

    chart_base64 = base64.b64encode(image_png).decode('utf-8')

    return JsonResponse({'chart': chart_base64})

def grouped_bar_chart(request):
    selected_date = request.GET.get('date')

    if selected_date:
        sales = VegetableSale.objects.filter(date=selected_date)

        labels = [sale.vegetable for sale in sales]
        purchase_totals = [sale.purchase_price * sale.quantity for sale in sales]
        selling_totals = [sale.selling_price * sale.quantity for sale in sales]

        x = np.arange(len(labels))
        width = 0.35

        fig, ax = plt.subplots()
        ax.bar(x - width/2, purchase_totals, width, label='Purchase', color='orange')
        ax.bar(x + width/2, selling_totals, width, label='Selling', color='green')

        ax.set_xlabel('Vegetables')
        ax.set_ylabel('Price')
        ax.set_title(f'Purchase vs Selling Price on {selected_date}')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45)
        ax.legend()
        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        chart = base64.b64encode(image_png).decode('utf-8')
        plt.close()

        return JsonResponse({'chart': chart})
    else:
        return JsonResponse({'error': 'Date not provided'}, status=400)
    
def stacked_profit_loss_chart(request):
    selected_date = request.GET.get('date')

    if selected_date:
        sales = VegetableSale.objects.filter(date=selected_date)

        labels = [sale.vegetable for sale in sales]
        profit_values = []
        loss_values = []

        for sale in sales:
            profit_or_loss = (sale.selling_price - sale.purchase_price) * sale.quantity
            if profit_or_loss > 0:
                profit_values.append(profit_or_loss)
                loss_values.append(0)
            else:
                profit_values.append(0)
                loss_values.append(abs(profit_or_loss))

        x = np.arange(len(labels))
        width = 0.6

        fig, ax = plt.subplots()
        ax.bar(x, profit_values, width, label='Profit', color='green')
        ax.bar(x, loss_values, width, bottom=profit_values, label='Loss', color='red')

        ax.set_xlabel('Vegetables')
        ax.set_ylabel('Amount')
        ax.set_title(f'Stacked Profit and Loss Chart on {selected_date}')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45)
        ax.legend()
        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        chart = base64.b64encode(image_png).decode('utf-8')
        plt.close()

        return JsonResponse({'chart': chart})
    else:
        return JsonResponse({'error': 'Date not provided'}, status=400)
    


def monthly_analysis(request):
    return render(request, 'sales/monthly-analysis.html')



def monthly_analysis_data(request):
    month_str = request.GET.get('month')
    if not month_str:
        return JsonResponse({'error': 'Month not provided'}, status=400)

    try:
        year, month = map(int, month_str.split('-'))
    except ValueError:
        return JsonResponse({'error': 'Invalid month format'}, status=400)

    sales = VegetableSale.objects.filter(date__year=year, date__month=month)

    total_investment = 0
    total_revenue = 0
    total_profit = 0
    total_loss = 0
    result = {}

    for sale in sales:
        vegetable_name = sale.vegetable

        if vegetable_name not in result:
            result[vegetable_name] = {
                'quantity': 0,
                'profit': 0,
                'loss': 0,
                'total_purchase_value': 0,
                'total_selling_value': 0
            }

        if sale.purchase_price is not None and sale.selling_price is not None and sale.quantity is not None:
            purchase_value = sale.purchase_price * sale.quantity
            selling_value = sale.selling_price * sale.quantity

            result[vegetable_name]['total_purchase_value'] += purchase_value
            result[vegetable_name]['total_selling_value'] += selling_value
            result[vegetable_name]['quantity'] += sale.quantity

            profit_or_loss = (sale.selling_price - sale.purchase_price) * sale.quantity
            if profit_or_loss >= 0:
                result[vegetable_name]['profit'] += profit_or_loss
                total_profit += profit_or_loss
            else:
                result[vegetable_name]['loss'] += abs(profit_or_loss)
                total_loss += abs(profit_or_loss)

            total_investment += purchase_value
            total_revenue += selling_value

    vegetable_data = [
        {'vegetable': k, 'quantity': v['quantity'], 'profit': v['profit'], 'loss': v['loss']}
        for k, v in result.items()
    ]

    summary_data = {
        'total_investment': total_investment,
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'total_loss': total_loss,
    }

    # 🎯 Quantity Analysis Chart using matplotlib
    vegetable_names = [item['vegetable'] for item in vegetable_data]
    quantities = [item['quantity'] for item in vegetable_data]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(vegetable_names, quantities, color='lightgreen')
    plt.xlabel('Vegetables')
    plt.ylabel('Total Quantity')
    plt.title(f'Vegetable Quantity Analysis - {month_str}')
    plt.xticks(rotation=45)
    plt.tight_layout()

    for bar in bars:
        height = bar.get_height()
        plt.annotate(f'{height}', xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points", ha='center')

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    plt.close()

    image_base64 = base64.b64encode(image_png).decode('utf-8')
    chart_url = f'data:image/png;base64,{image_base64}'

    return JsonResponse({
        'vegetables': vegetable_data,
        'summary': summary_data,
        'quantity_chart': chart_url,  # 📊 Base64 image chart included
    })
