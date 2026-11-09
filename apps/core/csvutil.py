import csv
from django.http import HttpResponse
def safe(v):
    v='' if v is None else str(v)
    return "'"+v if v[:1] in ('=','+','-','@','\t','\r') else v   # blocks spreadsheet formula injection
def csv_response(name,header,rows):
    r=HttpResponse(content_type='text/csv'); r['Content-Disposition']=f'attachment; filename="{name}"'; w=csv.writer(r); w.writerow(header)
    for row in rows: w.writerow([safe(c) for c in row])
    return r
