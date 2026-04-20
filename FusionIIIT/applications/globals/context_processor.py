from django.db.models import Q

from .models import HoldsDesignation


# def designation(request):
#     all_designation = HoldsDesignation.objects.exclude(designation__name='student')
#     designation_dictionary = {}
#     for i in all_designation:
#         key, value = str(i).split(' - ')
#         if key in designation_dictionary.keys():
#             designation_dictionary[key].append(value)
#         else:
#             designation_dictionary[key] = [value]
#     return {
#         'all_designation': designation_dictionary,
#     }

def designation(request):
    if request.user.is_authenticated():
        desig = HoldsDesignation.objects.filter(working=request.user)
        all_designation = []
        all_designation_labels = []
        for i in desig:
            all_designation.append(str(i.designation))
            all_designation_labels.append(str(i.designation.full_name))
        return {
            'all_designation': all_designation,
            'all_designation_labels': all_designation_labels,
            'designat': desig,
            'rspc_active_role': request.session.get('rspc_active_role', ''),
            'rspc_active_role_label': request.session.get('rspc_active_role_label', ''),
        }
    else:
        return {
            'all_designation': [],
            'all_designation_labels': [],
            'designat': [],
            'rspc_active_role': '',
            'rspc_active_role_label': '',
        }
