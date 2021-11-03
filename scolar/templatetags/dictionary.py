from django import template
from django.forms import BoundField
from django.utils.html import format_html
register = template.Library()

@register.filter('session_from_inscription_periode')
def session_from_inscription_periode(inscription_periode, periode_):
    """
    usage example {{ inscription_periode|session_from_inscription_periode:periode }}
    """
    session=''
    try:
        return inscription_periode.inscription.formation.periodes.get(periode=periode_).session
    except Exception:
        return session

@register.filter('get_value_from_dict')
def get_value_from_dict(dict_data, key):
    """
    usage example {{ your_dict|get_value_from_dict:your_key }}
    """
    if key:
        return dict_data.get(key)
    
@register.filter('value_from_obj')
def value_from_obj(obj, key):
    """
    usage example {{ your_dict|get_value_from_dict:your_key }}
    """
    if key:
        return obj.__dict__.get(key)

@register.filter('addstr')
def addstr(str1,str2):
    return str(str1)+str(str2)

@register.filter('topercent')
def percent(value,total):
    return value/total

@register.filter('sub')
def sub(value, arg):
    return value - arg

@register.filter
def as_percentage_of(part, whole):
    try:
        return round( (float(part) / float(whole) * 100),2)
    except (ValueError, ZeroDivisionError):
        return 0.00
 
@register.filter('multiply')
def multiply(qty1, qty2):
    return qty1 * qty2

@register.filter('tostr')
def tostr(str1):
    return str(str1)

@register.filter('decision_full')
def decision_full(str1):
    DECISIONS_JURY={
            'C':'En cours',
            'A':'Admis',
            'AR':'Admis avec Rachat',
            'R':'Redouble',
            'F':'Abandon',
            'M':'Maladie',
            'N':'Non Admis',
        }
    return DECISIONS_JURY[str1]

@register.filter('startswith')
def startswith(text, starts):
    return str(text).startswith(starts)

FR_EN_DICT={
    'Juin':'June',
    'Juillet':'July',
    'Janvier':'January',
    'Février':'February',
    'Octobre':'October',
    'Novembre':'November',
    'Décembre':'December',
    "Ingénieur d'état en Informatique":"Computer science engineer",
    "Master Académique":"Master of Science (MSc)",
    "1ère année":"1st year",
    "1ère année - Second Cycle":"1st year - 2nd Cycle",
    "2ème année - Second Cycle":"2nd year - 2nd Cycle ",
    "3ème année - Second Cycle":"3rd year - 2nd Cycle ",
    "2ème année":"2nd year",
    "Second Cycle":"2nd Cycle",
    "Classes préparatoires":"Preparatory classes",
    "Département de la formation préparatoire":"Department of preparatory training",
    "Département d'ingénierie de l'information et des systèmes informatiques":"Department of information and computer systems engineering",
    "1ère année - Classes Préparatoires (CP)":"1st year preparatory class",
    "2ème année - Classes Préparatoires (CP)":"2nd year preparatory class",
    
  
}
@register.filter 
def english(fr):
    """
    returns translation of fr
    """
    return FR_EN_DICT.get(fr)
FR_AR_DICT={
'Congé académique (année blanche) pour raisons médicales':'عطلة أكاديمية سنة بيضاء لاسباب صحية ',
'Congé académique (année blanche) pour raisons personnelles':'عطلة أكاديمية سنة بيضاء لاسباب شخصية',
'Congé académique (année blanche) pour raisons personnelles (Covid 19)':'عطلة أكاديمية سنة بيضاء لاسباب شخصية كوفيد 19',
'Congé académique (année blanche) pour raisons familiales':'عطلة أكاديمية سنة بيضاء لاسباب عائلية'

}
@register.filter 
def arabic(fr):
    """
    returns translation of fr to ar
    """
    return FR_AR_DICT.get(fr)

@register.filter 
def nom_mois(date):
    """
    returns name of the month on french
    """
    MOIS=[
        '',
        'Janvier',
        'Février',
        'Mars',
        'Avril',
        'Mai',
        'Juin',
        'Juillet',
        'Août',
        'Septembre',
        'Octobre',
        'Novembre',
        'Décembre'
        ]
    if date:
        return MOIS[date.month]
    else:
        return MOIS[0]

@register.filter 
def form_field(form, key):
    """
    returns field from forms.fields[key]
    """
    if key not in form.fields.keys():
        return None
    
    boundField = BoundField(form, form.fields[key], key)
    return boundField



@register.filter
def next(some_list, current_index):
    """
    Returns the next element of the list using the current index if it exists.
    Otherwise returns an empty string.
    """
    try:
        return some_list[int(current_index) + 1] # access the next element
    except:
        return '' # return empty string in case of exception

@register.filter
def previous(some_list, current_index):
    """
    Returns the previous element of the list using the current index if it exists.
    Otherwise returns an empty string.
    """
    try:
        return some_list[int(current_index) - 1] # access the previous element
    except:
        return '' # return empty string in case of exception


@register.simple_tag
def setvar(val=None):
  return int(val)
