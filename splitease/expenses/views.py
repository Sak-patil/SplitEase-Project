from django.shortcuts import render, get_object_or_404, redirect
from .models import Trip, Expense, Debt
from django.contrib.auth.models import User
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
# 1. CREATE TRIP VIEW
# This view handles showing the trip creation form and saving the new trip to the database.from django.contrib.auth.forms import UserCreationForm

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully!")
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'expenses/signup.html', {'form': form})

def create_trip(request):
    if request.method == "POST":
        # Get basic trip info from the form
        name = request.POST.get('name')
        description = request.POST.get('description')
        # getlist is used because 'members' is a multiple-choice selection
        member_ids = request.POST.getlist('members') 

        # Create the Trip object in the database
        new_trip = Trip.objects.create(name=name, description=description)
        
        # Link the selected members to this trip (ManyToMany Relationship)
        for m_id in member_ids:
            user = User.objects.get(id=m_id)
            new_trip.members.add(user)
        
        # Redirect to the dashboard of the newly created trip
        return redirect('trip_dashboard', trip_id=new_trip.id)

    # If it's a GET request, show the form with all registered users available to pick
    users = User.objects.all()
    return render(request, 'expenses/trip_detail.html', {'users': users})


# 2. ADD EXPENSE VIEW
# This handles the math of splitting the bill and updating the 'Debt' table.
def add_expense(request, trip_id):
    # Fetch the specific trip or show a 404 error if not found
    trip = get_object_or_404(Trip, id=trip_id)
    
    if request.method == "POST":
        # 1. Extract data from the POST request
        description = request.POST.get('description')
        amount = Decimal(request.POST.get('amount'))
        payer_id = request.POST.get('payer')
        payer = get_object_or_404(User, id=payer_id)

        # 2. Save the Expense record for history/tracking
        Expense.objects.create(
            trip=trip,
            description=description,
            amount=amount,
            paid_by=payer,
            category=request.POST.get('category')
        )

        # 3. Calculation Logic: Calculate the individual share
        members = trip.members.all()
        num_members = members.count()
        
        if num_members > 0:
            share = amount / num_members

            # 4. Update "Who owes Whom"
            # We loop through everyone. If they aren't the payer, they owe the payer money.
            for member in members:
                if member != payer:
                    # get_or_create finds the specific debt link between these two people
                    debt, created = Debt.objects.get_or_create(
                        trip=trip,
                        from_user=member,  # The Debtor
                        to_user=payer      # The Creditor
                    )
                    # Add the new share to their existing debt
                    debt.amount += share
                    debt.save()

        # Redirect to the dashboard to see the updated calculations
        return redirect('trip_dashboard', trip_id=trip.id)

    # Show the expense form
    return render(request, 'expenses/add_expense.html', {'trip': trip})


# 3. TRIP DASHBOARD VIEW
# This view pulls all the data together to show the final "Who owes Whom" list.
def trip_dashboard(request, trip_id):
    # Get the trip details
    trip = get_object_or_404(Trip, id=trip_id)
    
    # Get all non-zero debts for this trip to show on the dashboard
    debts = Debt.objects.filter(trip=trip).exclude(amount=0)
    
    context = {
        'trip': trip,
        'debts': debts,
    }
    return render(request, 'expenses/dashboard.html', context)

@login_required
def settle_debt(request, debt_id):
    # Find the specific debt relationship
    debt = get_object_or_404(Debt, id=debt_id)
    
    # Logic: Mark as paid by setting amount to 0
    if request.method == "POST":
        debt.amount = 0
        debt.save()
        
    return redirect('trip_dashboard', trip_id=debt.trip.id)

@login_required
def home(request):
    # 1. Get all trips the user belongs to
    my_trips = request.user.trips.all() 
    
    # 2. Get specific debts
    to_pay_list = Debt.objects.filter(from_user=request.user).exclude(amount=0)
    to_receive_list = Debt.objects.filter(to_user=request.user).exclude(amount=0)
    
    # 3. Calculate Totals for the Dashboard
    total_to_pay = to_pay_list.aggregate(Sum('amount'))['amount__sum'] or 0
    total_to_receive = to_receive_list.aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'my_trips': my_trips,
        'to_pay': to_pay_list,
        'to_receive': to_receive_list,
        'total_to_pay': total_to_pay,
        'total_to_receive': total_to_receive,
    }
    return render(request, 'expenses/home.html', context)