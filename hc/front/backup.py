import csv
from django.utils.encoding import smart_str
from django.http import HttpResponse

def checks_summary(request, file_name, q):
    # Response content type
    response = HttpResponse(content_type='text/csv')
    # Decide the file name
    file_name = "{}_checks_summary.csv".format(file_name)
    response['Content-Disposition'] = 'attachment; filename={}'.format(file_name)
 
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))

    # Write the headers
    writer.writerow([
            smart_str(u"Name"),
            smart_str(u"Created"),
            smart_str(u"Timeout Period"),
            smart_str(u"Grace Period"),
            smart_str(u"Nag Status"),
            smart_str(u"Status")

        ])
    for check in q:
        writer.writerow([
            smart_str(check.name),
            smart_str(check.created),
            smart_str(check.timeout),
            smart_str(check.grace),
            smart_str(check.nag_status),
            smart_str(check.get_status())
        ])
    return response

def check_log(request, file_name, q):
    # Response content type
    response = HttpResponse(content_type='text/csv')
    # Decide the file name
    file_name = "{}_check_log.csv".format(file_name)
    response['Content-Disposition'] = 'attachment; filename={}'.format(file_name)
 
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))

    # Write the headers
    writer.writerow([
            smart_str(u"Date"),
            smart_str(u"IP"),
            smart_str(u"Protocol"),
            smart_str(u"User Agent")

        ])
    for ping in q:
        writer.writerow([
            smart_str(ping.created),
            smart_str(ping.remote_addr),
            smart_str(ping.scheme),
            smart_str(ping.ua)
        ])
    return response
