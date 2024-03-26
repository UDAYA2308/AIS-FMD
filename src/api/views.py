import datetime
import os

import gspread
from apps.core.models import MasterLedger, Budget
from apps.core.serializer import MasterLedgerSerializer
from django.http import JsonResponse
from oauth2client.service_account import ServiceAccountCredentials
from rest_framework.decorators import api_view

SERVICE_FILE_LOCATION = os.environ["SERVICE_FILE_LOCATION"]
EXCEL_FILE_NAME = os.environ["EXCEL_FILE_NAME"]

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Authorize using the service account credentials
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_FILE_LOCATION, SCOPES)
client = gspread.authorize(creds)
SHEET_ID = os.environ["EXCEL_SHEET_ID"]


@api_view(['GET'])
def get_committee_budget(request):
    json_list = []
    for budget in Budget.objects.all().order_by('-StartDate'):
        committees = budget.Committees.split(',')
        budgets = budget.Budgets.split(',')
        json_obj = {
            'semester': budget.Semester,
            'start_date': budget.StartDate,
            'end_date': budget.EndDate,
            'committee': committees,
            'budget': budgets
        }
        json_list.append(json_obj)

    return JsonResponse(json_list, safe=False)


@api_view(['GET'])
def get_master_ledger_data(request):
    serializer = MasterLedgerSerializer(MasterLedger.objects.all(), many=True)
    return JsonResponse(serializer.data, safe=False)


@api_view(["POST"])
def update_database(request):
    # update Master Ledger
    # wks = sh.worksheet_by_title("Master Ledger")
    # data = wks.get_all_values()

    sheet = client.open_by_key(SHEET_ID).worksheet("Master Ledger")
    data = sheet.get_all_values()

    header = data[0]
    records = data[1:]

    instances = []
    for record in records:
        instance_data = dict(zip(header, record))
        instance_data['Date'] = instance_data.get('Date') if instance_data.get(
            'Date') else datetime.datetime.now().strftime('%Y-%m-%d')
        instance_data['Amount'] = instance_data.get('Amount') if instance_data.get('Amount') else 0
        instance_data = {key: value if value != '' else "N/A" for key, value in instance_data.items() if key != ''}

        instances.append(MasterLedger(**instance_data))

    # Delete existing records and bulk create new records
    MasterLedger.objects.all().delete()
    MasterLedger.objects.bulk_create(instances)

    master_ledger_count = len(instances)

    # update Budgeting

    # wks = sh.worksheet_by_title("Budgeting")
    # data = wks.get_all_values()
    sheet = client.open_by_key(SHEET_ID).worksheet("Budgeting")
    data = sheet.get_all_values()
    records = data[1:]

    instances = []
    for record in records:
        if all(record):
            json_obj = {
                'Semester': record[0],
                'StartDate': record[1],
                'EndDate': record[2],
                'Committees': record[3],
                'Budgets': record[4]
            }
            instances.append(Budget(**json_obj))

    # Delete existing records and bulk create new records
    Budget.objects.all().delete()
    Budget.objects.bulk_create(instances)
    budget_count = len(instances)

    return JsonResponse({"message": f"""Database updated Successfully!!!!""",
                         "No of Master ledger records": master_ledger_count,
                         "No of Budget records": budget_count,
                         }, safe=False)
