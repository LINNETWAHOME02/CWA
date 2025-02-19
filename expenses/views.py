from django.shortcuts import render, redirect, get_object_or_404
from .models import Member
import pandas as pd
from django.http import HttpResponse, HttpResponseForbidden
from reportlab.pdfgen import canvas
from io import BytesIO
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.contrib.auth.forms import UserCreationForm
from .forms import CustomUserCreationForm

@login_required
def dashboard(request):
    if request.user.is_superuser:
        # Superuser sees all members
        members = Member.objects.all()
    else:
        # Regular users see only their members
        members = Member.objects.filter(user=request.user)
    return render(request, 'dashboard.html', {'members': members})


@login_required
def upload_excel(request):
    if request.method == 'POST' and request.FILES['excel_file']:
        file = request.FILES['excel_file']
        df = pd.read_excel(file)

        # Clean columns and handle missing values
        df.columns = [col.strip().title() for col in df.columns]

        for index, row in df.iterrows():
            contributions = {}
            months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
                      'November', 'December']

            # Force annual_target to 6000 if missing
            annual_target = float(row.get('Annual Target', 6000.00))

            for month in months:
                # Force numeric values (default to 0)
                value = row.get(month, 0)
                try:
                    contributions[month] = float(value)
                except:
                    contributions[month] = 0.0

            # Ensure account_number is treated as a string
            account_number = str(row.get('Account Number', ''))

            Member.objects.update_or_create(
                user=request.user,
                account_number=account_number,
                defaults={
                    'name': row['Name'],
                    'phone': str(row.get('Phone', '')),
                    'annual_target': annual_target,
                    'monthly_contributions': contributions  # GUARANTEED to be a dict
                }
            )
        return redirect('dashboard')
    return render(request, 'upload.html')

@login_required
def generate_report(request, member_id):
    member = get_object_or_404(Member, id=member_id)

    # Render a confirmation page before generating the PDF
    return render(request, 'report.html', {'member': member})


def generate_pdf(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    buffer = BytesIO()

    # Create PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Use ReportLab styles, not Tailwind
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    body_style = styles['BodyText']

    elements.append(Paragraph(f"Member Report: {member.name}", title_style))

    # # Title
    # elements.append(Paragraph(f"<b>Contribution Report: {member.name}</b>", styles['Title']))

    # Member Details
    details = [
        ["Account Number:", member.account_number],
        ["Phone:", member.phone],
        # Updated lines (no parentheses after total_contributed/deficit):
        ["Total Contributed:", f"KES {member.total_contributed:.2f}"],
        ["Total Deficit:", f"KES {member.total_deficit:.2f}"]
    ]
    details_table = Table(details, colWidths=[150, 150])
    elements.append(details_table)

    # Calculate total paid for Jan-Mar
    total_paid = sum(float(member.monthly_contributions.get(month, 0))
                    for month in ['January', 'February', 'March'])

    # Build contributions table
    contributions_data = [["Month", "Paid (KES)", "Expected (KES)", "Deficit (KES)"]]

    for month in ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']:
        paid = float(member.monthly_contributions.get(month, 0))
        
        # Calculate expected and deficit
        if month == 'March':
            expected = float(member.annual_target)
            deficit = max(expected - total_paid, 0)  # Only show deficit in March
        else:
            expected = 0.0
            deficit = 0.0  # No deficit calculation for other months

        contributions_data.append([
            month,
            f"{paid:.2f}",
            f"{expected:.2f}",
            f"{deficit:.2f}" if deficit > 0 else "0.00"
        ])


    contributions_table = Table(contributions_data)
    contributions_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(contributions_table)

    doc.build(elements)
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')


@login_required
def edit_contributions(request, member_id):
    member = get_object_or_404(Member, id=member_id)

    # Restrict access: Only owner or superuser can edit
    if not request.user.is_superuser and member.user != request.user:
        return HttpResponseForbidden("You don't have permission to edit this member.")

    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']

    # Calculate expected values
    annual_months = ['January', 'February', 'March']
    expected_annual = float(member.annual_target) / 3  # 2000 KES/month
    expected_per_month = {
        month: expected_annual if month in annual_months else 0.0
        for month in months
    }

    if request.method == 'POST':
        contributions = {}
        for month in months:
            amount = request.POST.get(month, 0)
            contributions[month] = float(amount) if amount else 0

        member.monthly_contributions = contributions
        member.save()
        return redirect('dashboard')

    return render(request, 'edit_contributions.html', {
        'member': member,
        'months': months,
        'expected_per_month': expected_per_month,  # Pass dictionary
        'annual_months': annual_months
    })


def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'registration/login.html', {'error': 'Invalid credentials'})
    return render(request, 'registration/login.html')

def user_logout(request):
    logout(request)
    return redirect('login')

def delete_member(request, member_id):
    member = get_object_or_404(Member, id=member_id, user=request.user)
    member.delete()
    return redirect('dashboard')

def delete_all(request):
    if request.method == 'POST':
        Member.objects.filter(user=request.user).delete()
    return redirect('dashboard')
