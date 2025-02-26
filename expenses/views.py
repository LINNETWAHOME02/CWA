from datetime import datetime
import tempfile
import os

from django.shortcuts import render, redirect, get_object_or_404
from .models import Member
import pandas as pd
from django.http import HttpResponse, HttpResponseForbidden, Http404
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
from django import forms


@login_required
def dashboard(request):
    try:
        selected_year = int(request.GET.get('year', datetime.now().year))
    except:
        selected_year = datetime.now().year

    # Get available years with data
    members = Member.objects.filter(user=request.user)
    years = list(members.values_list('year', flat=True)
                 .distinct()
                 .order_by('-year'))

    if not years:
        years = [datetime.now().year]
        selected_year = datetime.now().year
    else:
        # Ensure selected_year exists in available years
        if selected_year not in years:
            selected_year = years[0]  # Use first available year

    members_data = Member.objects.filter(
        user=request.user,
        year=selected_year
    ).order_by('name')

    return render(request, 'dashboard.html', {
        'members': members_data,
        'selected_year': selected_year,
        'years': years
    })


class UploadForm(forms.Form):
    excel_file = forms.FileField()
    year = forms.IntegerField()
    sheet_name = forms.ChoiceField(required=False)  # Add field for sheet selection


# UPLOAD EXCEL FUNCTIONALITY
@login_required
def upload_excel(request):
    current_year = datetime.now().year
    years = range(2019, current_year + 1)

    if request.method == 'POST':
        if 'uploaded_excel_path' in request.session:
            # Process multi-sheet file after sheet selection
            return handle_multi_sheet_upload(request, years)
        else:
            # Initial file upload processing
            return handle_initial_upload(request, years)
    else:
        # GET request - show empty form
        form = UploadForm()
        return render(request, 'upload.html', {
            'form': form,
            'years': reversed(list(years)),
        })


def handle_multi_sheet_upload(request, years):
    """Process multi-sheet Excel file after sheet selection"""
    # Get session data
    tmp_path = request.session.get('uploaded_excel_path')
    year = request.session.get('uploaded_year')
    excel_file_name = request.session.get('uploaded_excel_name')
    selected_sheet = request.POST.get('sheet_name')

    if not selected_sheet:
        return render(request, 'upload.html', {
            'error': 'Please select a sheet.',
            'sheet_names': request.session.get('sheet_names', []),
            'excel_file_name': excel_file_name,
            'year': year,
            'years': reversed(list(years)),
        })

    try:
        with pd.ExcelFile(tmp_path) as xls:
            if selected_sheet not in xls.sheet_names:
                raise ValueError(f"Sheet '{selected_sheet}' not found")

            df = pd.read_excel(xls, sheet_name=selected_sheet)

        # Process data rows
        process_dataframe(df, request.user, year)

        # Cleanup
        cleanup_upload_session(request, tmp_path)

        return redirect(f'/?year={year}')

    except Exception as e:
        cleanup_upload_session(request, tmp_path)
        return render(request, 'upload.html', {
            'error': f'Error: {str(e)}',
            'years': reversed(list(years)),
        })


def handle_initial_upload(request, years):
    """Handle initial file upload (first step)"""
    form = UploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, 'upload.html', {
            'form': form,
            'years': reversed(list(years)),
        })

    year = form.cleaned_data['year']
    excel_file = request.FILES['excel_file']

    try:
        with pd.ExcelFile(excel_file) as xls:
            sheet_names = xls.sheet_names

        if len(sheet_names) > 1:
            # Save to temporary file for sheet selection
            return handle_multi_sheet_case(excel_file, year, sheet_names, request)
        else:
            # Process single sheet immediately
            return handle_single_sheet_case(excel_file, year, sheet_names, request)

    except Exception as e:
        return render(request, 'upload.html', {
            'error': f'Error: {str(e)}',
            'years': reversed(list(years)),
        })


def handle_multi_sheet_case(excel_file, year, sheet_names, request):
    """Handle multi-sheet Excel file"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        for chunk in excel_file.chunks():
            tmp_file.write(chunk)
        tmp_path = tmp_file.name

    # Store in session
    request.session.update({
        'uploaded_excel_path': tmp_path,
        'uploaded_year': year,
        'uploaded_excel_name': excel_file.name,
        'sheet_names': sheet_names
    })

    return render(request, 'upload.html', {
        'sheet_names': sheet_names,
        'excel_file_name': excel_file.name,
        'year': year,
        'years': reversed(list(range(2019, datetime.now().year + 1))),
    })


def handle_single_sheet_case(excel_file, year, sheet_names, request):
    """Handle single-sheet Excel file"""
    with pd.ExcelFile(excel_file) as xls:
        df = pd.read_excel(xls, sheet_name=sheet_names[0])

    process_dataframe(df, request.user, year)
    return redirect(f'/?year={year}')


def process_dataframe(df, user, year):
    """Process DataFrame and create/update members"""
    if 'Name' not in df.columns or 'Account Number' not in df.columns:
        raise ValueError("Excel file must contain 'Name' and 'Account Number' columns")

    for _, row in df.iterrows():
        phone = str(row.get('Phone', '')).strip().replace(' ', '')

        member_data = {
            'name': row['Name'].strip(),
            'phone': phone,
            'monthly_contributions': {
                month: float(row.get(month, 0))
                for month in [
                    'January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'
                ]
            }
        }

        Member.objects.update_or_create(
            user=user,
            account_number=str(row['Account Number']).strip(),
            year=year,
            defaults=member_data
        )


def cleanup_upload_session(request, tmp_path=None):
    """Cleanup temporary files and session data"""
    # Delete temporary file if exists
    if tmp_path and os.path.exists(tmp_path):
        try:
            os.unlink(tmp_path)
        except PermissionError:
            pass

    # Clear session keys
    session_keys = [
        'uploaded_excel_path', 'uploaded_year',
        'uploaded_excel_name', 'sheet_names'
    ]
    for key in session_keys:
        if key in request.session:
            del request.session[key]


# REPORT GENERATING FUNCTIONALITY
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

    # Member Details
    details = [
        ["Account Number:", member.account_number],
        ["Phone:", member.phone],
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


# EDITING MEMBERS CONTRIBUTIONS FUNCTIONALITY
@login_required
def edit_contributions(request, member_id):
    member = get_object_or_404(Member, id=member_id)

    # Restrict access: Only owner or superuser can edit
    if not request.user.is_superuser and member.user != request.user:
        return HttpResponseForbidden("You don't have permission to edit this member.")

    # Get current year from member object or request
    current_year = request.GET.get('year', member.year)

    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']

    # Calculate expected values
    annual_months = ['January', 'February', 'March']
    expected_annual = float(member.annual_target) / 3
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
        # Redirect to dashboard with preserved year
        return redirect(f'/?year={current_year}')

    return render(request, 'edit_contributions.html', {
        'member': member,
        'months': months,
        'expected_per_month': expected_per_month,
        'annual_months': annual_months,
        'current_year': current_year  # Pass to template
    })


# USER AUTHENTICATION FUNCTIONALITY
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


# DELETE MEMBER(S) DATA OR ALL MEMBERS DATA FUNCTIONALITY
@login_required
def delete_member(request, member_id):
    member = get_object_or_404(Member, id=member_id, user=request.user)
    current_year = request.GET.get('year', datetime.now().year)  # Get current year
    member.delete()
    return redirect(f'/?year={current_year}')  # Redirect with year parameter


@login_required
def delete_all(request):
    if request.method == 'POST':
        try:
            selected_year = int(request.POST.get('year', datetime.now().year))
            Member.objects.filter(user=request.user, year=selected_year).delete()
        except ValueError:
            selected_year = datetime.now().year

    return redirect(f'/?year={selected_year}')  # Preserve year in redirect
