from django.shortcuts import render, get_object_or_404, redirect
from .models import Trip, Expense, Debt, TripMember
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
        description = request.POST.get('description') or ""
        # Get member names and whatsapp numbers arrays
        member_names = request.POST.getlist('member_names[]')
        member_whatsapp = request.POST.getlist('member_whatsapp[]')

        # Create the Trip object in the database
        new_trip = Trip.objects.create(name=name, description=description, created_by=request.user)

        # Add current user as a member
        new_trip.members.add(request.user)

        # Add creator as TripMember with their whatsapp
        TripMember.objects.create(
            trip=new_trip,
            user=request.user,
            whatsapp_number=request.user.username,
            name=request.user.username
        )

        # Process each member
        for member_name, member_whatsapp_num in zip(member_names, member_whatsapp):
            member_name = member_name.strip()
            member_whatsapp_num = member_whatsapp_num.strip()

            if member_name and member_whatsapp_num:
                # Try to find existing user by username (case-insensitive)
                try:
                    user = User.objects.get(username__iexact=member_name)
                    # Add to trip members
                    new_trip.members.add(user)
                    # Create TripMember with user
                    TripMember.objects.create(
                        trip=new_trip,
                        user=user,
                        whatsapp_number=member_whatsapp_num,
                        name=user.username
                    )
                except User.DoesNotExist:
                    # For non-registered members, create a temporary user account
                    # Generate a unique username
                    temp_username = member_name.lower().replace(' ', '_') + '_' + str(new_trip.id)
                    # Create user with random password
                    temp_user = User.objects.create_user(
                        username=temp_username,
                        password='temp123456',
                        first_name=member_name
                    )
                    # Add to trip members
                    new_trip.members.add(temp_user)
                    # Create TripMember with temporary user
                    TripMember.objects.create(
                        trip=new_trip,
                        user=temp_user,
                        whatsapp_number=member_whatsapp_num,
                        name=member_name
                    )

        messages.success(request, f"Trip '{name}' created successfully!")
        # Redirect to the dashboard of the newly created trip
        return redirect('trip_dashboard', trip_id=new_trip.id)

    # If it's a GET request, show the form
    available_users = User.objects.exclude(id=request.user.id)
    return render(request, 'expenses/trip_detail.html', {'available_users': available_users})


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

    # Get all non-zero debts for this trip
    debts = Debt.objects.filter(trip=trip).exclude(amount=0)

    # Prepare debt data with WhatsApp links
    simplified_debts = []
    for debt in debts:
        # Get the debtor's TripMember info - try by user first, then by name
        whatsapp_number = None
        try:
            # Try to find by user
            trip_member = TripMember.objects.get(trip=trip, user=debt.from_user)
            whatsapp_number = trip_member.whatsapp_number
        except TripMember.DoesNotExist:
            try:
                # Try to find by name
                trip_member = TripMember.objects.get(trip=trip, name=debt.from_user.username)
                whatsapp_number = trip_member.whatsapp_number
            except TripMember.DoesNotExist:
                whatsapp_number = None

        # Get display names (first_name for temp users, username for regular)
        debtor_name = debt.from_user.first_name if debt.from_user.first_name else debt.from_user.username
        creditor_name = debt.to_user.first_name if debt.to_user.first_name else debt.to_user.username
        
        # Generate WhatsApp message
        message = f"Hey {debtor_name}, just a friendly nudge from SplitEase! 🌍 Regarding our trip {trip.name}, {creditor_name} covered an expense and your share comes to ₹{debt.amount}. Check the home dashboard of SplitEase for the full breakdown whenever you're free. Thanks! 🤝"

        simplified_debts.append({
            'debtor': debt.from_user,
            'creditor': debt.to_user,
            'debtor_id': debt.from_user.id,
            'creditor_id': debt.to_user.id,
            'amount': debt.amount,
            'whatsapp_number': whatsapp_number,
            'message': message,
        })

    # Calculate remaining people to pay
    remaining_to_pay = len(simplified_debts)

    context = {
        'trip': trip,
        'simplified_debts': simplified_debts,
        'remaining_to_pay': remaining_to_pay,
        'total_members': trip.members.count(),
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
def settle_debt_simplified(request, trip_id, debtor_id, creditor_id):
    """
    Simplified settlement for net debt calculation.
    Only the creditor can confirm settlement.
    """
    trip = get_object_or_404(Trip, id=trip_id)
    debtor = get_object_or_404(User, id=debtor_id)
    creditor = get_object_or_404(User, id=creditor_id)
    
    # Security: Only the creditor can mark debt as settled
    if request.user != creditor:
        messages.error(request, "Only the person who is owed money can confirm settlement.")
        return redirect('trip_dashboard', trip_id=trip.id)
    
    if request.method == "POST":
        # Find and settle all debts from debtor to creditor
        debts = Debt.objects.filter(trip=trip, from_user=debtor, to_user=creditor)
        for debt in debts:
            debt.amount = 0
            debt.save()
        
        messages.success(request, f"Payment from {debtor.username} confirmed as settled!")
    
    return redirect('trip_dashboard', trip_id=trip.id)

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

    # 4. Check which trips the user has paid expenses for
    trip_payer_status = {}
    for trip in my_trips:
        has_paid = Expense.objects.filter(trip=trip, paid_by=request.user).exists()
        trip_payer_status[trip.id] = has_paid

    context = {
        'my_trips': my_trips,
        'to_pay': to_pay_list,
        'to_receive': to_receive_list,
        'total_to_pay': total_to_pay,
        'total_to_receive': total_to_receive,
        'trip_payer_status': trip_payer_status,
    }
    return render(request, 'expenses/home.html', context)

def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    trip_id = expense.trip.id # Save ID to redirect back
    
    if request.method == "POST":
        # Professional logic: Adjust the debts before deleting the expense
        # For simplicity in this hackathon stage, we just remove the record
        expense.delete()
        return redirect('trip_dashboard', trip_id=trip_id)
    
    return redirect('trip_dashboard', trip_id=trip_id)

@login_required
def delete_trip(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    
    if request.method == "POST":
        trip.delete()
        messages.success(request, f"Trip '{trip.name}' deleted successfully!")
        return redirect('home')
    
    return redirect('home')