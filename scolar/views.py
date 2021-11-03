# Create your views here.
from django.shortcuts import render, get_object_or_404
import locale
import babel.numbers
from num2words import num2words
from datetime import datetime
from djmoney.money import Money
from decimal import Decimal
from django_tables2.config import RequestConfig
import threading
import logging
from django.db import IntegrityError
from django.db import transaction
from django.template.loader import render_to_string
import requests
from django.contrib import messages
from scolar.models import *
import os
from django.utils.safestring import mark_safe
from scolar.tables import OrganismeTable, OrganismeFilter, PFETable, PFEFilter, ValidationTable, MatiereTable, \
    MatiereFilter, InscriptionEtudiantDocumentsTable, InscriptionEtudiantTable, InscriptionFilter, \
    InscriptionGroupeTable, InscriptionTable, \
    EvaluationCompetenceElementTable, EvaluationTable, AbsenceEnseignantFilter, AbsenceEnseignantTable, \
    AbsenceEtudiantFilter, AbsenceEtudiantTable, ActiviteChargeConfigTable, \
    CompetenceElementTable, CompetenceFamilyTable, CompetenceTable, MatiereCompetenceElementTable, DiplomeTable, \
    DepartementTable, SpecialiteTable, PeriodeTable, DeliberationFormationTable, PVFilter, \
    ProgrammeTable, FormationTable, PlanificationTable, EtudiantFilter, EtudiantTable, EnseignantFilter, \
    EnseignantTable, SectionTable, FormationFilter, \
    GroupeAllFilter, GroupeAllTable, GroupeTable, NotesFormationTable, TutoratTable, ModuleFeedbackTable, ModuleFilter, \
    ModuleTable, ChargeEnseignantTable, PVTable, PVEnseignantTable, \
    CoordinationModuleFilter, SemainierTable, FeedbackTable, AnneeUnivTable, SeanceTable, ActiviteEtudiantFilter, \
    ActiviteEtudiantTable, ActiviteTable, ActiviteFilter, \
    PreinscriptionTable, ResidenceUnivTable, PreinscriptionFilter, ExamenTable, ExamenFilter
from functools import reduce
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import EmailMessage, send_mass_mail
from django.views.generic.base import TemplateView
from django.db.models.signals import post_save, m2m_changed, post_delete, pre_delete
from django.db.models import Q, Count, Sum, When, Value, Case, F, Max, Min, Avg, OuterRef, Subquery
from django.dispatch import receiver
from scolar.forms import EnseignantDetailForm, AbsenceEtudiantReportSelectionForm, SeanceEtudiantSelectionForm, \
    OTPImportFileForm, PFEDetailForm, OrganismeForm, SelectOrCreateOrganismeForm, COMPETENCE_EVAL, \
    InscriptionUpdateForm, SelectChargeConfigForm, SelectPVSettingsForm, ChargeFilterForm, MatiereCompetenceForm, \
    NotesPFEUpdateForm, SeanceSelectionForm, PlanificationImportFileForm, EDTForm, CompetenceForm, FeedbackUpdateForm, \
    SelectModuleForm, ReleveNotesUpdateForm, ImportDeliberationForm, AbsencesForm, ImportNotesForm, NotesUpdateForm, \
    ImportFileForm, ImportAffectationForm, MatiereFormHelper, ImportFeedbackForm, \
    SelectionFormationForm, SelectSingleModuleForm, ImportAffectationDiplomeForm, ImportChargeForm, \
    SelectPVAnnuelSettingsForm, \
    CommissionValidationCreateForm, ExamenCreateForm, SeanceSallesReservationForm, SurveillanceUpdateForm, \
    InstitutionDetailForm, \
    SelectionInscriptionForm, ValidationPreInscriptionForm, EDTImportFileForm, EDTSelectForm, ExamenSelectForm, \
    AffichageExamenSelectForm, CreditForm
# from scolar.forms import *
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseNotFound, Http404
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, HTML, Button
from crispy_forms.bootstrap import TabHolder, Tab
from django.urls import reverse
from django import forms
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
import random
from bootstrap_datepicker_plus import DatePickerInput
from scolar.admin import settings
from jchart import Chart
from jchart.config import DataSet
from django.shortcuts import redirect
import urllib

# from tablib import Dataset, Databook
from django_select2.forms import ModelSelect2Widget, Select2Widget, ModelSelect2MultipleWidget, Select2MultipleWidget
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
import datetime
from django.core.files.storage import default_storage
from django.contrib.auth.models import Group
import decimal
from wkhtmltopdf.views import PDFTemplateView, render_pdf_from_template
from django.db.models.aggregates import Avg
from django.contrib.auth.decorators import user_passes_test, permission_required, \
    login_required

from django.db.models.expressions import ExpressionWrapper
from django.db.models.fields import FloatField, DecimalField
import re, string
import operator
from _ast import If, In
from django.core.exceptions import ObjectDoesNotExist
from django.core.files import File

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from uuid import uuid4
import pytz
from builtins import Exception



def exclude_columns(user):
    exclude_ = []
    if not user.is_authenticated:
        exclude_.append('edit')
        exclude_.append('admin')
    elif not (user.is_staff_only()):
        exclude_.append('admin')
        exclude_.append('edit')
    return exclude_


def assure_module(enseignant_, module_):
    if module_.coordinateur == enseignant_:
        return True
    else:
        activite_list = Activite.objects.filter(module__matiere=module_.matiere, assuree_par__in=[enseignant_]).exclude(
            type__startswith='E_')
        return activite_list.exists()


def assure_module_groupe(enseignant_, module_, groupe_):
    if module_.coordinateur == enseignant_:
        return True
    else:
        activite_list = Activite.objects.filter(module__matiere=module_.matiere, cible__in=[groupe_],
                                                assuree_par__in=[enseignant_]).exclude(type__startswith='E_')
        return activite_list.exists()


def get_groupe_list_from_str(student_set):
    """
        Cette fonction est utilisée dans l'import des activités à partir de FET export.
    """
    groupe_list = []
    str_groupe_list = student_set.split('+')
    for str_groupe in str_groupe_list:
        groupe_elements = str_groupe.split()
        formation_str = groupe_elements[0]
        section_str = groupe_elements[1]
        groupe_str = groupe_elements[2] if len(groupe_elements) == 3 else None
        if groupe_str:
            groupe = get_object_or_404(Groupe, code=groupe_str, section__code=section_str,
                                       section__formation__programme__code=formation_str,
                                       section__formation__annee_univ__encours=True)
        else:
            groupe = get_object_or_404(Groupe, code__isnull=True, section__code=section_str,
                                       section__formation__programme__code=formation_str,
                                       section__formation__annee_univ__encours=True)
        groupe_list.append(groupe)
    return groupe_list


def get_enseignant_list_from_str(teacher_set):
    """
        Cette fonction est utilisée pour retrouver la liste des enseignants de la base de Talents
        qui correspondent à la liste des enseignants générée dans les activités importées de l'export de FET.
        Attention, il faut que les noms de enseignants dans FET correspondent aux noms dans la base de Talents
    """
    enseignant_list = []
    str_enseignant_list = teacher_set.split('+')
    for str_enseignant in str_enseignant_list:
        enseignant_elements = str_enseignant.split()
        # traiter les noms composés
        prenom_initial = enseignant_elements[len(enseignant_elements) - 1]
        nom_ = enseignant_elements[0]
        for i in range(1, len(enseignant_elements) - 1):
            nom_ += ' ' + enseignant_elements[i]

        enseignant = Enseignant.objects.get(nom__icontains=nom_, prenom__startswith=prenom_initial)
        enseignant_list.append(enseignant)
    return enseignant_list


def get_type_activite_from_str(activity_tag):
    """
        Cette fonction est utilisée pour traduire les types d'activités dans l'export de FET vers le type d'activités dans la base
        de Talents.
        Attention, il faut uniformiser les notations avant la génération des EDT avec FET
    """
    TAG_TRANS = {
        'Cours': 'C',
        'eCours': 'C',
        'TD': 'TD',
        'eTD': 'TD',
        'TDp': 'TD',
        'TP': 'TP',
        'eTP': 'TP',
        'Projet': 'P',
    }
    return TAG_TRANS[activity_tag]


@login_required
def planning_import_from_fet(request):
    # if this is a POST request we need to process the form data
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = PlanificationImportFileForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            try:
                activite_file = request.FILES['file']

                dataset = Dataset(headers=['Students Sets', 'Subject', 'Teachers', 'Activity Tags', 'Total Duration'])
                imported_data = dataset.load(activite_file.read().decode('utf-8'), format='csv')
                periode_ = form.cleaned_data['periode']
                # supprimer toutes les activités du semestre avant d'importer les nouvelles
                Activite.objects.filter(module__formation__annee_univ__encours=True,
                                        module__periode__periode=periode_).delete()
                # insert imported_data in Activite table
                ligne_problem = ''
                for row in imported_data.dict:
                    try:
                        cible_ = get_groupe_list_from_str(row['Students Sets'])
                        module_ = Module.objects.get(matiere__code=row['Subject'].split()[0], periode__periode=periode_,
                                                     formation=cible_[0].section.formation)
                        activite_ = Activite.objects.create(
                            module=module_,
                            type=get_type_activite_from_str(row['Activity Tags']),
                            vh=round(decimal.Decimal(row['Total Duration']) / decimal.Decimal(2), 2),
                            repeter_chaque_semaine=True
                        )
                        try:
                            assuree_par_ = get_enseignant_list_from_str(row['Teachers'])
                        except Exception:
                            assuree_par_ = []
                            pass

                        for enseignant_ in assuree_par_:
                            activite_.assuree_par.add(enseignant_)

                        for groupe_ in cible_:
                            activite_.cible.add(groupe_)
                        activite_.save()
                    except Exception:
                        ligne_problem += str(row) + '\n'
                        continue
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "L'import des activités n'a pas réussit. Il doit y avoir un problème dans le format du fichier")
                    messages.info(request,
                                  "Merci de renseigner le semestre pour lequel vous voulez importer les activités pédagogiques.")
                    messages.info(request,
                                  "Le fichier doit être au format csv (généré par FET) avec les colonnes: 'Students Sets', 'Subject', 'Teachers', 'Activity Tags', 'Total Duration'")
                    return render(request, 'scolar/import.html',
                                  {'form': form, 'titre': 'Importer Planning à partir de FET'})
                    # redirect to a new URL:
            messages.success(request, "Les activités ont été importées avec succès")
            if len(ligne_problem) != 0:
                messages.warning(request, "Lignes avec erreurs:\n" + ligne_problem)
            return HttpResponseRedirect(reverse('planification_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = PlanificationImportFileForm()
    messages.info(request,
                  "Merci de renseigner le semestre pour lequel vous voulez importer les activités pédagogiques.")
    messages.info(request,
                  "Le fichier doit être au format csv (généré par FET) avec les colonnes: 'Students Sets', 'Subject', 'Teachers', 'Activity Tags', 'Total Duration'")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer Planning à partir de FET'})


JOUR_NUM = {
    'Dimanche': 0,
    'Lundi': 1,
    'Mardi': 2,
    'Mercredi': 3,
    'Jeudi': 4,
    'Vendredi': 5,
    'Samedi': 6
}


@login_required
def from_fet_to_google_agenda(request):
    # if this is a POST request we need to process the form data
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)

    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRET_FILE,
        scopes=settings.SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob')

    # Tell the user to go to the authorization URL.
    auth_url, _ = flow.authorization_url(prompt='consent')
    btn_list = {
        "Demande Code Autorisation": auth_url
    }

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = EDTImportFileForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            try:
                flow.fetch_token(code=form.cleaned_data['code'])
                service = build("calendar", "v3", credentials=flow.credentials)

                # start_datetime = datetime.datetime.now(tz=pytz.utc)

                timetable_file = request.FILES['file']
                dataset = Dataset()
                imported_data = dataset.load(timetable_file.read().decode('utf-8'), format='csv')

                cleaned_data = form.cleaned_data
                t = threading.Thread(target=task_from_fet_to_google_agenda,
                                     args=[cleaned_data, imported_data, service, request.user])
                t.setDaemon(True)
                t.start()
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "L'insertion des EDT n'a pas réussit. Il doit y avoir un problème dans le format du fichier")
                    messages.info(request,
                                  "Le fichier doit être au format csv (généré par FET) avec les colonnes: 'Activity Id', 'Day', 'Hour', 'Students Sets', 'Subject', 'Teachers', 'Activity Tags', 'Total Duration', Room'")
                    return render(request, 'scolar/import.html',
                                  {'form': form, 'titre': 'Insertion des EDT à partir de FET', 'btn_list': btn_list})
                    # redirect to a new URL:
            messages.success(request,
                             "L'insertion des EDT dans Google Agenda a été lancée. Une notification vous sera transmise aussitôt terminée.")
            return HttpResponseRedirect(reverse('home'))
            # if a GET (or any other method) we'll create a blank form
    else:
        messages.warning(request,
                         "Cliquez sur le bouton Demander Code Autorisation pour avoir le code d'autorisation Google.")
        form = EDTImportFileForm()
    messages.info(request,
                  "Le fichier doit être au format csv (généré par FET) avec les colonnes: 'Activity Id', 'Day', 'Hour', 'Students Sets', 'Subject', 'Teachers', 'Activity Tags', 'Total Duration', Room'")
    return render(request, 'scolar/import.html',
                  {'form': form, 'titre': 'Insérer les EDT dans Google Agenda à partir de FET', 'btn_list': btn_list})


def task_from_fet_to_google_agenda(cleaned_data, imported_data, service, user):
    try:
        start_date = cleaned_data['date_debut']
        end_date = cleaned_data['date_fin']

        # TODO : supprimer toutes les activités avant d'importer les nouvelles

        # insert imported_data in Google Agenda
        index_ = 0
        while index_ < len(imported_data.dict):
            try:
                # pour chque slot time une ligne portant le même activity id est créée dans le fichier
                # il faut donc isoler la 1ère et dernière ligne d'une même activité pour retrouver l'heure début et l'heure fin d'une activité
                first_ = index_
                last_ = index_
                # avancer jusqu'une nouvelle activité ou fin du fichier
                while last_ < len(imported_data.dict):
                    if imported_data.dict[last_].get("Activity Id") == imported_data.dict[first_].get("Activity Id"):
                        last_ += 1
                    else:
                        break
                last_ -= 1
                index_ = last_ + 1

                first_activity_row = imported_data.dict[first_]
                last_activity_row = imported_data.dict[last_]
                # ATTENETION: dans FET il faut remplacer Pause1 par 12h10-12h40
                start_time_string = first_activity_row.get("Hour").split('-')[0]  # TODO Convertir en heur
                start_time_h = int(start_time_string.split('h')[0])
                start_time_min = int(start_time_string.split('h')[1])

                end_time_string = last_activity_row.get("Hour").split('-')[1]  # TODO Convertir en heur
                end_time_h = int(end_time_string.split('h')[0])
                end_time_min = int(end_time_string.split('h')[1])

                week_day = JOUR_NUM[imported_data.dict[first_].get("Day")]

                # insérer un event dans l'agenda de chaque groupe cible de l'activité
                groupe_list = get_groupe_list_from_str(first_activity_row['Students Sets'])
                try:
                    enseignant_list = get_enseignant_list_from_str(first_activity_row['Teachers'])
                except:
                    email = EmailMessage('[Talents] Erreur lors de l\'insertion des EDT dans Google Agenda',
                                         'Bonjour,\n' +
                                         'Une erreur s\'est produite lors de l\'insertion des EDT dans Google Agenda' + '\n' +
                                         '==>  ' + first_activity_row['Teachers'] + '\n'
                                                                                    'Bien cordialement.\n' +
                                         'Département', to=[user.email])
                    if settings.EMAIL_ENABLED:
                        email.send(fail_silently=True)

                    enseignant_list = []
                    pass
                room_list = []
                try:
                    for code_salle_ in first_activity_row['Room'].split('+'):
                        room_list.append(Salle.objects.get(code=code_salle_))
                except Exception:
                    pass

                first_groupe = True
                for groupe_ in groupe_list:
                    if groupe_.gCal():
                        if first_groupe:
                            first_groupe = False
                            first_groupe_event = {
                                "summary": first_activity_row.get("Activity Tags") + " " + first_activity_row.get(
                                    "Subject") + " " + first_activity_row.get("Teachers"),
                                # "description": "Bar",
                                "start": {
                                    "dateTime": (start_date + datetime.timedelta(days=week_day, hours=start_time_h,
                                                                                 minutes=start_time_min)).isoformat(),
                                    "timeZone": "Africa/Algiers"
                                },
                                "end": {
                                    "dateTime": (start_date + datetime.timedelta(days=week_day, hours=end_time_h,
                                                                                 minutes=end_time_min)).isoformat(),
                                    "timeZone": "Africa/Algiers"
                                },
                                'attendees': [
                                    {'email': enseignant_.user.email} for enseignant_ in enseignant_list
                                ],
                                'recurrence': [
                                    'RRULE:FREQ=WEEKLY;UNTIL=' + end_date.strftime("%Y%m%dT%H%M%SZ"),
                                ],
                                'location': first_activity_row.get("Room"),
                                'conferenceData': {
                                    'createRequest': {
                                        "requestId": f"{uuid4().hex}",
                                        'conferenceSolutionKey': {
                                            'type': "hangoutsMeet"
                                        }
                                    }
                                }
                            }
                            if len(room_list) > 0:
                                for room in room_list:
                                    first_groupe_event['attendees'].append({'email': room.calendarId, 'resource': True})
                            first_event = service.events().insert(calendarId=groupe_.gCal().calendarId,
                                                                  body=first_groupe_event,
                                                                  conferenceDataVersion=1).execute()
                        else:
                            groupe_event = {
                                "summary": first_activity_row.get("Activity Tags") + " " + first_activity_row.get(
                                    "Subject") + " " + first_activity_row.get("Teachers"),
                                # "description": "Bar",
                                "start": {
                                    "dateTime": (start_date + datetime.timedelta(days=week_day, hours=start_time_h,
                                                                                 minutes=start_time_min)).isoformat(),
                                    "timeZone": "Africa/Algiers"
                                },
                                "end": {
                                    "dateTime": (start_date + datetime.timedelta(days=week_day, hours=end_time_h,
                                                                                 minutes=end_time_min)).isoformat(),
                                    "timeZone": "Africa/Algiers"
                                },
                                'recurrence': [
                                    'RRULE:FREQ=WEEKLY;UNTIL=' + end_date.strftime("%Y%m%dT%H%M%SZ"),
                                ],
                                'conferenceData': first_event['conferenceData'],
                                'location': first_groupe_event['location'],
                            }
                            service.events().insert(calendarId=groupe_.gCal().calendarId, body=groupe_event,
                                                    conferenceDataVersion=1).execute()
            except Exception:
                print('ERREUR A LA LIGNE N°' + str(index_) + ': ' + str(imported_data.dict[index_]))
                continue

        email = EmailMessage('[Talents] Insertion des EDT dans Google Agenda',
                             'Bonjour,\n' +
                             "L'insertion des EDT dans Google Agenda est terminée avec succès \n" +
                             'Bien cordialement.\n' +
                             'Département', to=[user.email]
                             )
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage('[Talents] Erreur lors de l\'insertion des EDT dans Google Agenda',
                                 'Bonjour,\n' +
                                 'Une erreur s\'est produite lors de l\'insertion des EDT dans Google Agenda' + '\n' +
                                 'Bien cordialement.\n' +
                                 'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)


@login_required
def clear_google_agenda(request):
    # if this is a POST request we need to process the form data
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)

    flow = Flow.from_client_secrets_file(
        settings.GOOGLE_CLIENT_SECRET_FILE,
        scopes=settings.SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob')

    # Tell the user to go to the authorization URL.
    auth_url, _ = flow.authorization_url(prompt='consent')
    btn_list = {
        "Demande Code Autorisation": auth_url
    }

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = EDTSelectForm(request.POST)

        # check whether it's valid:
        if form.is_valid():
            try:
                # service = build_gcal_service()
                flow.fetch_token(code=form.cleaned_data['code'])
                service = build("calendar", "v3", credentials=flow.credentials)

                cleaned_data = form.cleaned_data

                t = threading.Thread(target=task_clear_google_agenda, args=[cleaned_data, service, request.user])
                t.setDaemon(True)
                t.start()

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "Erreur lors de la demande de suppression des EDT de Google Agenda")
                    return render(request, 'scolar/import.html',
                                  {'form': form, 'titre': 'Suppression des EDT de Google Agenda', "btn_list": btn_list})
                    # redirect to a new URL:
            messages.success(request,
                             "La suppression des EDT de Google Agenda est en cours. Une notification vous sera transmise aussitôt terminée.")
            return HttpResponseRedirect(reverse('home'))
            # if a GET (or any other method) we'll create a blank form
    else:
        messages.warning(request,
                         "Cliquez sur le bouton Demander Code Autorisation pour avoir le code d'autorisation Google.")
        form = EDTSelectForm()
    messages.info(request, "Merci de renseigner formulaire pour indiquer quels EDT supprimer de Google Agenda.")
    return render(request, 'scolar/import.html',
                  {'form': form, 'titre': 'Suppression des EDT de Google Agenda', "btn_list": btn_list})


def task_clear_google_agenda(cleaned_data, service, user):
    try:
        start_date = cleaned_data['date_debut']
        end_date = cleaned_data['date_fin']
        google_calendar_list = cleaned_data['google_calendar_list']
        for calendar_ in google_calendar_list:
            page_token = None
            while True:
                events = service.events().list(calendarId=calendar_.calendarId,
                                               pageToken=page_token,
                                               timeMin=start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                               timeMax=end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                               singleEvents=True
                                               ).execute()
                for event_ in events['items']:
                    try:
                        service.events().delete(calendarId=calendar_.calendarId, eventId=event_["id"],
                                                sendUpdates="none").execute()
                    except Exception:
                        continue
                page_token = events.get('nextPageToken')
                if not page_token:
                    break
        email = EmailMessage('[Talents] Suppression des EDT de Google Agenda',
                             'Bonjour,\n' +
                             "La suppression des EDT de Google Agenda est terminée avec succès \n" +
                             'Bien cordialement.\n' +
                             'Département', to=[user.email]
                             )
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage('[Talents] Erreur lors de la suppression des EDT de Google Agenda',
                                 'Bonjour,\n' +
                                 'Une erreur s\'est produite lors de la suppression des EDT de Google Agenda' + '\n' +
                                 'Bien cordialement.\n' +
                                 'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)


def edt_list_view(request):
    # if this is a POST request we need to process the form data
    context = {}
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = EDTForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            form_data = form.cleaned_data
            groupe_ = form_data['groupe']
            etudiant_ = form_data['etudiant']
            enseignant_ = form_data['enseignant']
            if groupe_:
                context['groupe'] = Groupe.objects.get(id=groupe_)
            if enseignant_:
                context['enseignant'] = enseignant_
            if etudiant_:
                inscription_list = Inscription.objects.filter(etudiant=etudiant_, formation__annee_univ__encours=True)
                if inscription_list.exists():
                    context['inscription_list'] = inscription_list
    else:
        form = EDTForm()

    context['form'] = form
    context['titre'] = 'EDT Finder'
    messages.info(request, "Choisir un critère de recherche d'un EDT.")
    return render(request, 'scolar/edt_finder.html', context)


def releve_notes_update_view(request, inscription_pk):
    """
        Cette vue permet de modifier les notes post_delib et décision du jury pendant les délibérations
    """
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)
    inscription_ = Inscription.objects.get(id=inscription_pk)
    context = {}
    context['inscription'] = inscription_

    # if this is a POST request we need to process the form data

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ReleveNotesUpdateForm(inscription_pk, request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                # process the data in form.cleaned_data as required
                data = form.cleaned_data
                for periode_ in inscription_.inscription_periodes.all():
                    periode_.moy = data[periode_.periodepgm.code]
                    for ue_ in periode_.resultat_ues.all():
                        for resultat_ in ue_.resultat_matieres.all():
                            resultat_.moy_post_delib = data[resultat_.module.matiere.code]
                            resultat_.save(update_fields=['moy_post_delib'])
                inscription_.proposition_decision_jury = data['proposition_decision_jury']
                inscription_.save(update_fields=['proposition_decision_jury'])
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "Erreur lors de la modification des notes post délibération et/ou décision du conseil")
                    messages.info(request, "Merci d'utiliser ce formulaire pour le rachat (note post délibération)")
                    messages.info(request, "Ne pas oublier de renseigner la nouvelle décision du conseil.")
                    return render(request, 'scolar/releve_notes_update.html', {'form': form})
            messages.success(request, "Les modifications ont bien été enregistrées")
            return HttpResponseRedirect(
                reverse('deliberation_detail', kwargs={'formation_pk': inscription_.formation.id, }))
            # if a GET (or any other method) we'll create a blank form
    else:

        form = ReleveNotesUpdateForm(inscription_pk)
        context['form'] = form
        messages.info(request, "Merci d'utiliser ce formulaire pour le rachat (note post délibération)")
        messages.info(request, "Ne pas oublier de renseigner la nouvelle décision du conseil.")
    return render(request, 'scolar/releve_notes_update.html', context)


class ReleveNotesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/releve_notes.html'

    def test_func(self):
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        return self.request.user.is_staff_or_student_himself(inscription_.etudiant.matricule)

    def get_context_data(self, **kwargs):
        context = super(ReleveNotesView, self).get_context_data(**kwargs)
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))

        context['inscription'] = inscription_
        context['decision_jury'] = dict(DECISIONS_JURY)
        context['categorie_ue'] = dict(CAT_UE)
        context['date'] = datetime.date.today()
        # afficher les crédits uniquement pour CP
        # c'est ridicule mais a priori ça vient de la tutelle
        context['credits'] = 1 if inscription_.formation.programme.ordre <= 2 else None

        return context


class ReleveNotesPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/releve_notes_pdf.html'
    cmd_options = {
        'orientation': 'Landscape',
        'page-size': 'A4',

    }

    def test_func(self):
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        return self.request.user.is_staff_or_student_himself(inscription_.etudiant.matricule)

    def get_context_data(self, **kwargs):
        context = super(ReleveNotesPDFView, self).get_context_data(**kwargs)
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        self.filename = str(inscription_) + '.pdf'
        context['inscription'] = inscription_
        context['date'] = datetime.date.today()
        context['categorie_ue'] = dict(CAT_UE)
        context['decision_jury'] = dict(DECISIONS_JURY)
        context['pdf'] = 1
        # afficher les crédits uniquement pour CP
        # c'est ridicule mais a priori ça vient de la tutelle
        context['credits'] = 1 if inscription_.formation.programme.ordre <= 2 else None
        return context


# class ReleveNotesListPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
#     template_name = 'scolar/releve_notes_list_pdf.html'
#     cmd_options={
#         'orientation':'Landscape',
#         'page-size':'A4',
#         }
#     def test_func(self):
#         return self.request.user.is_scolarite()
#
#     def get_context_data(self, **kwargs):
#         context = super(ReleveNotesListPDFView, self).get_context_data(**kwargs)
#         formation_=Formation.objects.get(id=self.kwargs.get('formation_pk'))
#         inscription_list=formation_.inscriptions_actives().order_by('etudiant__nom', 'etudiant__prenom')
#         self.filename='RELEVES_ANNUELS_'+str(formation_)+'.pdf'
#         context['inscription_list'] = inscription_list
#         context['date'] = datetime.date.today()
#         context['categorie_ue']=dict(CAT_UE)
#         context['decision_jury']=dict(DECISIONS_JURY)
#         context['pdf']=1
#         # afficher les crédits uniquement pour CP
#         # c'est ridicule mais a priori ça vient de la tutelle
#         context['credits'] = 1 if formation_.programme.ordre <=2 else None
#         return context

@login_required
def releve_notes_list_pdf_view(request, formation_pk, periode_pk):
    if not (request.user.is_scolarite() or request.user.is_direction()):
        messages.error(request, "Vous n'avez pas la permission d'exécution de cette opération")
        return redirect('/accounts/login/?next=%s' % request.path)
    try:
        t = threading.Thread(target=task_releves_notes_pdf, args=[formation_pk, request.user])
        t.setDaemon(True)
        t.start()
        messages.success(request, "Votre demande de génération des relevés de notes est prise en compte.")
        messages.success(request, "Une notification vous sera transmise une fois la tâche terminée.")

    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: lors de génération des relevés de notes. Merci de le signaler à l'administrateur.")
    return HttpResponseRedirect(reverse('document_list'))


def task_releves_notes_pdf(formation_pk, user):
    try:
        context = {}
        cmd_options = {
            'orientation': 'Landscape',
            'page-size': 'A4',
        }

        formation_ = Formation.objects.get(id=formation_pk)
        inscription_list = formation_.inscriptions_pour_deliberations().order_by('etudiant__nom', 'etudiant__prenom')
        filename = 'RELEVES_ANNUELS_' + str(formation_) + '.pdf'
        context['inscription_list'] = inscription_list
        context['date'] = datetime.date.today()
        context['categorie_ue'] = dict(CAT_UE)
        context['decision_jury'] = dict(DECISIONS_JURY)
        context['pdf'] = 1
        # afficher les crédits uniquement pour CP
        # c'est ridicule mais a priori ça vient de la tutelle
        context['credits'] = 1 if formation_.programme.ordre <= 2 else None
        context['institution'] = user.institution()

        pdf_ = render_pdf_from_template(input_template='scolar/releve_notes_list_pdf.html',
                                        header_template=None,
                                        footer_template=None,
                                        context=context,
                                        cmd_options=cmd_options)
        email = EmailMessage('[Talents] Génération des relevés de notes de ' + str(formation_),
                             'Bonjour,\n' +
                             'La génération des relevés de notes de ' + str(formation_) + ' est terminée \n' +
                             'Veuillez trouver ci-joints les relevés\n' +
                             'Bien cordialement.\n' +
                             'Département', to=[user.email]  # +
                             # settings.STAFF_EMAILS['scolarite']+
                             # settings.STAFF_EMAILS['direction']
                             )
        email.attach(filename, pdf_, 'application/pdf')
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage(
                '[Talents] Erreur lors de la génération des relevés de notes de  la formation ' + str(formation_),
                'Bonjour,\n' +
                'Une erreur s\'est produite lors de la génération des relevés de notes de la formation ' + str(
                    formation_) + '\n' +
                'Bien cordialement.\n' +
                'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)


class ReleveNotesGlobalPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/releve_notes_global_pdf.html'
    cmd_options = {
        'orientation': 'Portrait',
        'page-size': 'A4',
    }

    def test_func(self):
        return self.request.user.is_staff_or_student_himself(self.kwargs.get('etudiant_pk'))

    def get_context_data(self, **kwargs):
        context = super(ReleveNotesGlobalPDFView, self).get_context_data(**kwargs)
        etudiant_ = Etudiant.objects.get(matricule=self.kwargs.get('etudiant_pk'))
        self.filename = str(etudiant_) + '.pdf'
        context['etudiant'] = etudiant_
        context['inscription_list'] = Inscription.objects.filter(etudiant=etudiant_,
                                                                 formation__programme__diplome=self.kwargs.get(
                                                                     'diplome_pk')).order_by(
            'formation__programme__ordre')
        context['departement_list'] = Departement.objects.all().order_by('cycle_ordre')
        context['date'] = datetime.date.today()
        context['categorie_ue'] = dict(CAT_UE)
        context['decision_jury'] = dict(DECISIONS_JURY)
        context['mention'] = dict(MENTION)
        return context


class CertificatPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/certificat_pdf.html'
    cmd_options = {
        'orientation': 'Landscape',
        'page-size': 'A4',
    }

    def test_func(self):
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        return self.request.user.is_staff_or_student_himself(inscription_.etudiant.matricule)

    def get_context_data(self, **kwargs):
        context = super(CertificatPDFView, self).get_context_data(**kwargs)
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        self.filename = 'CERTIFICAT_3L_' + str(inscription_) + '.pdf'
        context['inscription'] = inscription_
        context['date'] = datetime.date.today()
        context['range'] = ['f', 'o']  # f : first, r:right, o:other positions are used in template so it's important

        return context


class FicheInscriptionPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/fiche_inscription_pdf.html'
    cmd_options = {
        'orientation': 'Portrait',
        'page-size': 'A4',
    }

    def test_func(self):
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        return self.request.user.is_staff_or_student_himself(inscription_.etudiant.matricule)

    def get_context_data(self, **kwargs):
        context = super(FicheInscriptionPDFView, self).get_context_data(**kwargs)
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        inscription_annee_precedente_ = Inscription.objects.filter(etudiant=inscription_.etudiant,
                                                                   formation__annee_univ=inscription_.formation.annee_univ.annee_precedente(),
                                                                   formation__programme__diplome=inscription_.formation.programme.diplome
                                                                   )
        if inscription_annee_precedente_.count() == 1:
            inscription_annee_precedente_ = inscription_annee_precedente_.get()
        else:
            inscription_annee_precedente_ = None

        self.filename = 'FICHE_INSCRIPTION' + str(inscription_) + '.pdf'
        context['inscription'] = inscription_
        context['inscription_annee_precedente'] = inscription_annee_precedente_
        context['decision_jury'] = dict(DECISIONS_JURY)
        context['date'] = datetime.date.today()

        return context


# class CertificatListPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
#     template_name = 'scolar/certificat_list_pdf.html'
#     cmd_options={
#         'orientation':'Landscape',
#         'page-size':'A4',
#         }
#     def test_func(self):
#         return self.request.user.is_scolarite() or self.request.user.is_direction()
#
#     def get_context_data(self, **kwargs):
#         context = super(CertificatListPDFView, self).get_context_data(**kwargs)
#         formation_=Formation.objects.get(id=self.kwargs.get('formation_pk'))
#         inscription_list=formation_.inscriptions_actives().order_by('etudiant__nom', 'etudiant__prenom')
#         self.filename='CERTIFICATS_3L_'+str(formation_)+'.pdf'
#         context['inscription_list'] = inscription_list
#         context['date'] = datetime.date.today()
#         context['range']=['f','r']
#
#         return context

@login_required
def certificat_3l_list_pdf_view(request, formation_pk, periode_pk):
    if not (request.user.is_scolarite() or request.user.is_direction()):
        messages.error(request, "Vous n'avez pas la permission d'exécution de cette opération")
        return redirect('/accounts/login/?next=%s' % request.path)
    try:
        t = threading.Thread(target=task_certificat_3l_list_pdf, args=[formation_pk, request.user])
        t.setDaemon(True)
        t.start()
        messages.success(request, "Votre demande de génération des certificats de scolarité est prise en compte.")
        messages.success(request, "Une notification vous sera transmise une fois la tâche terminée.")

    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: lors de génération des certificats de scolarité. Merci de le signaler à l'administrateur.")
    return HttpResponseRedirect(reverse('document_list'))


def task_certificat_3l_list_pdf(formation_pk, user):
    try:
        context = {}
        cmd_options = {
            'orientation': 'Landscape',
            'page-size': 'A4',
        }

        formation_ = Formation.objects.get(id=formation_pk)
        inscription_list = formation_.pre_inscriptions().order_by('etudiant__nom', 'etudiant__prenom')
        filename = 'CERTIFICATS_3L_' + str(formation_) + '.pdf'
        context['inscription_list'] = inscription_list
        context['date'] = datetime.date.today()
        context['range'] = ['f', 'o']
        context['institution'] = user.institution()

        pdf_ = render_pdf_from_template(input_template='scolar/certificat_list_pdf.html',
                                        header_template=None,
                                        footer_template=None,
                                        context=context,
                                        cmd_options=cmd_options)
        email = EmailMessage('[Talents] Génération des certificats de scolarité 3L de ' + str(formation_),
                             'Bonjour,\n' +
                             'La génération des certificats de scolarité 3L de ' + str(
                                 formation_) + ' est terminée \n' +
                             'Veuillez trouver ci-joints les certifictas\n' +
                             'Bien cordialement.\n' +
                             'Département', to=[user.email]  # +
                             # settings.STAFF_EMAILS['scolarite']+
                             # settings.STAFF_EMAILS['direction']
                             )
        email.attach(filename, pdf_, 'application/pdf')
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage(
                '[Talents] Erreur lors de la génération des certificats de scolarité de la formation ' + str(
                    formation_),
                'Bonjour,\n' +
                'Une erreur s\'est produite lors de la génération des certificats de scolarité de la formation ' + str(
                    formation_) + '\n' +
                'Bien cordialement.\n' +
                'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)


class CertificatCongesPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/certificat_conges_pdf.html'
    cmd_options = {
        'orientation': 'Landscape',
        'page-size': 'A4',
    }

    def test_func(self):
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        return self.request.user.is_staff_or_student_himself(inscription_.etudiant.matricule)

    def get_context_data(self, **kwargs):
        context = super(CertificatCongesPDFView, self).get_context_data(**kwargs)
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        self.filename = 'ATTESATATION_CONGES_ACAD' + str(inscription_) + '.pdf'
        context['inscription'] = inscription_
        context['raison'] = dict(DECISIONS_JURY)[inscription_.decision_jury]
        context['date'] = datetime.date.today()

        return context


class CertificatOldPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/certificat_old_pdf.html'
    cmd_options = {
        'orientation': 'Landscape',
        'page-size': 'A4',
    }

    def test_func(self):
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        return self.request.user.is_staff_or_student_himself(inscription_.etudiant.matricule)

    def get_context_data(self, **kwargs):
        context = super(CertificatOldPDFView, self).get_context_data(**kwargs)
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        self.filename = 'CERTIFICAT_Fr_Ar' + str(inscription_) + '.pdf'
        context['inscription'] = inscription_
        context['date'] = datetime.date.today()
        return context


# class CertificatOldListPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
#     template_name = 'scolar/certificat_old_list_pdf.html'
#     cmd_options={
#         'orientation':'Landscape',
#         'page-size':'A4',
#         }
#     def test_func(self):
#         return self.request.user.is_scolarite() or self.request.user.is_direction()
#
#     def get_context_data(self, **kwargs):
#         context = super(CertificatOldListPDFView, self).get_context_data(**kwargs)
#         formation_=Formation.objects.get(id=self.kwargs.get('formation_pk'))
#         inscription_list=formation_.inscriptions_actives().order_by('etudiant__nom', 'etudiant__prenom')
#         self.filename='CERTIFICAT_Fr_Ar'+str(formation_)+'.pdf'
#         context['inscription_list'] = inscription_list
#         context['date'] = datetime.date.today()
#         return context

@login_required
def certificat_2l_list_pdf_view(request, formation_pk, periode_pk):
    if not (request.user.is_scolarite() or request.user.is_direction()):
        messages.error(request, "Vous n'avez pas la permission d'exécution de cette opération")
        return redirect('/accounts/login/?next=%s' % request.path)
    try:
        t = threading.Thread(target=task_certificat_2l_list_pdf, args=[formation_pk, request.user])
        t.setDaemon(True)
        t.start()
        messages.success(request, "Votre demande de génération des certificats de scolarité est prise en compte.")
        messages.success(request, "Une notification vous sera transmise une fois la tâche terminée.")

    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: lors de génération des certificats de scolarité. Merci de le signaler à l'administrateur.")
    return HttpResponseRedirect(reverse('document_list'))


def task_certificat_2l_list_pdf(formation_pk, user):
    try:
        context = {}
        cmd_options = {
            'orientation': 'Landscape',
            'page-size': 'A4',
        }

        formation_ = Formation.objects.get(id=formation_pk)
        inscription_list = formation_.pre_inscriptions().order_by('etudiant__nom', 'etudiant__prenom')
        filename = 'CERTIFICAT_Fr_Ar' + str(formation_) + '.pdf'
        context['inscription_list'] = inscription_list
        context['date'] = datetime.date.today()
        context['institution'] = user.institution()

        pdf_ = render_pdf_from_template(input_template='scolar/certificat_old_list_pdf.html',
                                        header_template=None,
                                        footer_template=None,
                                        context=context,
                                        cmd_options=cmd_options)
        email = EmailMessage('[Talents] Génération des certificats de scolarité 2L de ' + str(formation_),
                             'Bonjour,\n' +
                             'La génération des certificats de scolarité 3L de ' + str(
                                 formation_) + ' est terminée \n' +
                             'Veuillez trouver ci-joints les certifictas\n' +
                             'Bien cordialement.\n' +
                             'Département', to=[user.email]  # +
                             # settings.STAFF_EMAILS['scolarite']+
                             # settings.STAFF_EMAILS['direction']
                             )
        email.attach(filename, pdf_, 'application/pdf')
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage(
                '[Talents] Erreur lors de la génération des certificats de scolarité de la formation ' + str(
                    formation_),
                'Bonjour,\n' +
                'Une erreur s\'est produite lors de la génération des certificats de scolarité de la formation ' + str(
                    formation_) + '\n' +
                'Bien cordialement.\n' +
                'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)


class ReleveECTSListPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/releve_ects_list_pdf.html'
    cmd_options = {
        'orientation': 'Portrait',
        'page-size': 'A4',
    }

    def test_func(self):
        return self.request.user.is_scolarite() or self.request.user.is_direction()

    def get_context_data(self, **kwargs):
        context = super(ReleveECTSListPDFView, self).get_context_data(**kwargs)
        formation_ = Formation.objects.get(id=self.kwargs.get('formation_pk'))
        inscription_list = formation_.inscriptions_actives().order_by('etudiant__nom', 'etudiant__prenom')
        self.filename = 'RELEVE_ECTS_' + str(formation_) + '.pdf'
        context['inscription_list'] = inscription_list
        context['date'] = datetime.date.today()
        return context


TYPE_DOC_URL = {
    'C3L': 'certificat_list_pdf',
    'C2L': 'certificat_old_list_pdf',
    'RP1': 'releve_notes_provisoire_list_pdf',
    'RP2': 'releve_notes_provisoire_list_pdf',
    'RA': 'releve_notes_list_pdf',
    'RECTS': 'releve_ects_list_pdf',
    'FPFE': 'pfe_fiche_list_pdf',
}


def document_list_view(request):
    if not (request.user.is_scolarite() or request.user.is_direction() or request.user.is_stage()):
        messages.error(request, "Vous n'avez pas la permission d'exécution de cette opération")
        return redirect('/accounts/login/?next=%s' % request.path)
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SelectionFormationForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                form_data = form.cleaned_data
                formation_ = form_data['formation']
                type_doc_ = form_data['type_document']
                periode_ = form_data['periode'] if form_data['periode'] else 0
                return HttpResponseRedirect(
                    reverse(TYPE_DOC_URL[type_doc_], kwargs={'formation_pk': formation_.id, 'periode_pk': periode_}))
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: La génération de la liste de documents demandés s'est arrêtée avec des erreurs. Merci de le signaler à l'administrateur.")
                    render(request, 'scolar/import.html', {'form': form, 'titre': 'Génération de documents groupés.'})
            messages.success(request, "La génération des documents s'est terminée avec succès!")
            # redirect to a new URL:

    # if a GET (or any other method) we'll create a blank form
    else:
        form = SelectionFormationForm()
        messages.info(request, "Merci de renseigner les critères de choix des documents à générer.")
        messages.warning(request,
                         "Attention! Assurez vous que les données sont bien présentes dans la base (inscriptions pour les certificats, délibérations pour les relevés.")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Génération de documents groupés'})


class ResidenceUnivCreateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, CreateView):
    model = ResidenceUniv
    fields = ['nom', 'adresse', 'tel', 'wilaya', 'commune']
    template_name = 'scolar/create.html'
    success_message = "La résidence universitaire a été créée avec succès!"

    def test_func(self):
        return self.request.user.is_staff_only()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        try:
            form.fields['wilaya'] = forms.ModelChoiceField(
                queryset=Wilaya.objects.all().order_by('nom'),
                label=u"Wilaya",
                widget=ModelSelect2Widget(
                    model=Wilaya,
                    search_fields=['nom__icontains', ],
                    # attrs={'style':'width:800px; height:10px;'}
                ),
                help_text="Choisir une wilaya. Tapez deux espaces pour avoir toute la liste.",
                required=True
            )
            form.fields['commune'] = forms.ModelChoiceField(
                queryset=Commune.objects.all().order_by('nom'),
                label=u"Commune",
                widget=ModelSelect2Widget(
                    model=Commune,
                    search_fields=['nom__icontains', ],
                    dependent_fields={'wilaya': 'wilaya'},
                    # attrs={'style':'width:800px; height:10px;'}
                ),
                help_text="Choisir une commune. Tapez deux espaces pour avoir toute la liste.",
                required=True
            )

            form.helper.add_input(Submit('submit', 'Enregistrer', css_class='btn-primary'))
            form.helper.add_input(
                Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
            self.success_url = reverse('settings')
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request, "ERREUR: lors de la création d'une résidence universitaire.")

        return form


class ResidenceUnivListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/list.html'

    def test_func(self):
        return self.request.user.is_staff_only()

    def get_queryset(self, **kwargs):
        return ResidenceUniv.objects.all().order_by('nom')

    def get_context_data(self, **kwargs):
        context = super(ResidenceUnivListView, self).get_context_data(**kwargs)
        table = ResidenceUnivTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['titre'] = "Liste des résidence universitaire"
        context['table'] = table
        context['back'] = reverse('settings')
        btn_list = {}
        btn_list['Créer Résidence'] = reverse('residenceuniv_create')
        context['btn_list'] = btn_list

        return context


class PreinscriptionCreateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, CreateView):
    model = Preinscription

    fields = ['inscription', 'wilaya_residence', 'commune_residence', 'interne', 'residence_univ', 'adresse_principale',
              'photo', 'tel', 'numero_securite_sociale', 'quittance']
    template_name = 'scolar/preinscription_create.html'
    success_message = "Votre pré-inscription est enregsitrée avec succès!"

    def test_func(self):
        return self.request.user.is_etudiant()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        try:
            inscription_list = Inscription.objects.filter(etudiant=self.request.user.etudiant, decision_jury='X',
                                                          formation__annee_univ__annee_univ__gte=self.request.user.annee_encours().annee_univ)
            form.fields['inscription'] = forms.ModelChoiceField(label='Inscription en',
                                                                queryset=inscription_list,
                                                                initial=0,
                                                                required=True)
            form.fields[
                'photo'].help_text = "Si vous voulez changer de photo, merci de déposer ici un scan d'une photo d'identité. Taille maximale 1M."
            form.fields['quittance'].required = True
            form.fields[
                'quittance'].help_text = "Merci de déposer ici un scan ou une photo de la quittance de payement des frais d'inscription. Taille maximale 1M."
            form.fields[
                'numero_securite_sociale'].help_text = "Merci d'indiquer le numéro figurant sur l'ATS ou carte CHIFA."
            form.fields['wilaya_residence'] = forms.ModelChoiceField(
                queryset=Wilaya.objects.all().order_by('nom'),
                label=u"Wilaya de résidence principale",
                initial=self.request.user.etudiant.wilaya_residence,
                widget=ModelSelect2Widget(
                    model=Wilaya,
                    search_fields=['nom__icontains', ],
                    # attrs={'style':'width:800px; height:10px;'}
                ),
                help_text="Choisir une wilaya. Tapez deux espaces pour avoir toute la liste.",
                required=True
            )
            form.fields['commune_residence'] = forms.ModelChoiceField(
                queryset=Commune.objects.all().order_by('nom'),
                label=u"Commune de résidence principale",
                initial=self.request.user.etudiant.commune_residence,
                widget=ModelSelect2Widget(
                    model=Commune,
                    search_fields=['nom__icontains', ],
                    dependent_fields={'wilaya_residence': 'wilaya'},
                    # attrs={'style':'width:800px; height:10px;'}
                ),
                help_text="Choisir une commune. Tapez deux espaces pour avoir toute la liste.",
                required=True
            )
            form.fields['interne'].initial = self.request.user.etudiant.interne
            if self.request.user.etudiant.interne and self.request.user.etudiant.residence_univ:
                residence_univ_candidate = ResidenceUniv.objects.filter(
                    reduce(lambda x, y: x | y,
                           [Q(nom__icontains=mot) for mot in self.request.user.etudiant.residence_univ.split()]))
                if residence_univ_candidate.exists():
                    form.fields['residence_univ'].initial = residence_univ_candidate[0]
            form.fields['adresse_principale'].initial = self.request.user.etudiant.addresse_principale
            form.fields['adresse_principale'].required = True
            form.fields['tel'].initial = self.request.user.etudiant.tel
            form.fields['tel'].help_text = "Composé de 10 chiffres sans espaces ou autre caratères."
            form.fields['tel'].required = True
            urls_reglement = ''
            for inscription_ in inscription_list:
                if inscription_.formation.programme.departement.reglement.name:
                    urls_reglement += '<a href="' + inscription_.formation.programme.departement.reglement.url + '">' + inscription_.formation.programme.code + '</a>,'
            form.fields['engagement'] = forms.BooleanField(required=True,
                                                           initial=False,
                                                           label=mark_safe(
                                                               'J\'ai lu et j\'approuve le réglement intérieur des études (disponible ici: ' + urls_reglement + ')')
                                                           )
            form.helper.add_input(Submit('submit', 'Envoyer', css_class='btn-primary'))
            form.helper.add_input(
                Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
            self.success_url = reverse('home')
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: Vous n'êtes pas sur une liste de pré-inscription. Merci de le signaler à l'administrateur si vous devez vous pré-inscrire à une formation.")

        return form


@receiver(post_save, sender=Preinscription)
def email_preinscription_surveillance(sender, update_fields, instance, created, **kwargs):
    if created:
        email = EmailMessage(
            'Inscription de ' + str(instance.inscription.etudiant) + ' en ' + str(instance.inscription.formation),
            'Bonjour,\n' +
            "Une nouvelle demande d'inscription a été déposée: " + '\n'
                                                                   "Candidat : " + str(
                instance.inscription.etudiant) + '\n'
                                                 "Année d'étude: " + str(instance.inscription.formation) + '\n'
                                                                                                           'Veuillez traiter cette demande d\'inscription en effectuant les vérifications nécessaires.\n' +
            'La demande est accessible à partir de votre compte sous le menu Pré-Inscriptions, ou en suivant ce lien:' + '\n' +
            settings.PROTOCOLE_HOST + reverse('preinscription_list') + '\n' +
            'Bien cordialement.\n' +
            'Département',
            to=[instance.inscription.formation.programme.assistant.user.email] if not settings.DEBUG else [
                'y_challal@esi.dz'])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)


class PreinscriptionListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/filter_list.html'

    def test_func(self):
        return self.request.user.is_staff_only()

    def get_queryset(self, **kwargs):
        return Preinscription.objects.all()

    def get_context_data(self, **kwargs):
        context = super(PreinscriptionListView, self).get_context_data(**kwargs)
        filter_ = PreinscriptionFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()
        table = PreinscriptionTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['titre'] = "Liste des demandes d'inscription"
        context['back'] = reverse('home')
        return context


def validation_preinscription_view(request, inscription_pk):
    if not (request.user.is_surveillance() or request.user.is_scolarite() or request.user.is_direction()):
        messages.error(request, "Vous n'avez pas la permission d'exécution de cette opération")
        return redirect('/accounts/login/?next=%s' % request.path)
    inscription_ = get_object_or_404(Inscription, id=inscription_pk)
    inscription_annee_precedente_ = Inscription.objects.filter(etudiant=inscription_.etudiant,
                                                               formation__annee_univ=inscription_.formation.annee_univ.annee_precedente(),
                                                               formation__programme__diplome=inscription_.formation.programme.diplome
                                                               )
    if inscription_annee_precedente_.count() == 1:
        inscription_annee_precedente_ = inscription_annee_precedente_.get()
    else:
        inscription_annee_precedente_ = None

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ValidationPreInscriptionForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                form_data = form.cleaned_data
                if form_data['valider_inscription'] == 'V':
                    inscription_.etudiant.wilaya_residence = inscription_.preinscription.wilaya_residence
                    inscription_.etudiant.commune_residence = inscription_.preinscription.commune_residence
                    inscription_.etudiant.addresse_principale = inscription_.preinscription.adresse_principale.upper()
                    inscription_.etudiant.tel = inscription_.preinscription.tel
                    inscription_.etudiant.interne = inscription_.preinscription.interne
                    if inscription_.preinscription.interne:
                        if inscription_.preinscription.residence_univ:
                            inscription_.etudiant.residence_univ = inscription_.preinscription.residence_univ.nom.upper()

                    inscription_.etudiant.numero_securite_sociale = inscription_.preinscription.numero_securite_sociale
                    if inscription_.preinscription.photo.name:
                        if inscription_.etudiant.photo.name != inscription_.etudiant.photo.field.upload_to + '/' + 'anonymous-user.jpg':
                            inscription_.etudiant.photo.delete()
                        uploaded_file_name, uploaded_file_extension = os.path.splitext(
                            inscription_.preinscription.photo.name)
                        # photo_file_name=inscription_.etudiant.photo.field.upload_to+'/'+inscription_.etudiant.matricule.replace('/','-')+uploaded_file_extension
                        photo_file_name = inscription_.etudiant.matricule.replace('/', '-') + uploaded_file_extension
                        inscription_.etudiant.photo = File(inscription_.preinscription.photo, photo_file_name)
                    if inscription_.preinscription.quittance.name:
                        inscription_.quittance.delete()
                        uploaded_file_name, uploaded_file_extension = os.path.splitext(
                            inscription_.preinscription.quittance.name)
                        # quittance_file_name=inscription_.quittance.field.upload_to+'/'+str(inscription_).replace('/','-').replace(' ','_')+uploaded_file_extension
                        quittance_file_name = str(inscription_.etudiant.matricule).replace('/',
                                                                                           '-') + uploaded_file_extension
                        inscription_.quittance = File(inscription_.preinscription.quittance, quittance_file_name)
                    inscription_.decision_jury = 'C'
                    inscription_.etudiant.save()
                    inscription_.save(update_fields=['decision_jury', 'quittance'])
                    inscription_.preinscription.photo.delete()
                    inscription_.preinscription.quittance.delete()
                    Preinscription.objects.filter(inscription=inscription_).delete()

                    # Envoie de notification, relevé et certificat à l'étudiant
                    email = EmailMessage('Votre Inscription en ' + str(inscription_.formation),
                                         'Bonjour ' + inscription_.etudiant.prenom + ',\n' +
                                         "Votre inscription en : " + str(inscription_.formation) + ' est confirmée.\n'
                                                                                                   'Veuillez trouver ci-joints votre certificat de scolarité et votre relevé de notes de l\'année passée s\'il y a lieu.\n' +
                                         'Ces documents sont une copie, seuls les originaux font foi.\n' +
                                         "Pour récupérer les originaux, merci de vous rapprocher de la surveillance et remettre:\n" +
                                         "1- l'original de la quittance de payement des frais d'inscription.\n" +
                                         "2- la fiche d'inscription ci-jointe signée.\n" +
                                         'Bien cordialement.\n' +
                                         'Département', to=[inscription_.etudiant.user.email,
                                                            request.user.email] if not settings.DEBUG else [
                            'y_challal@esi.dz'])

                    cmd_options = {
                        'orientation': 'Landscape',
                        'page-size': 'A4',
                    }
                    certificat_filename = 'CERTIFICAT_' + str(inscription_).replace(' ', '_') + '.pdf'
                    context = {}
                    context['inscription'] = inscription_
                    context['date'] = datetime.date.today()
                    context['categorie_ue'] = dict(CAT_UE)
                    context['decision_jury'] = dict(DECISIONS_JURY)
                    context['pdf'] = 1
                    context['range'] = ['f', 'o']
                    # afficher les crédits uniquement pour CP
                    # c'est ridicule mais a priori ça vient de la tutelle
                    context['credits'] = 1 if inscription_.formation.programme.ordre <= 2 else None
                    context['signature'] = 1
                    context['institution'] = inscription_.etudiant.user.institution()
                    certificat_pdf_ = render_pdf_from_template(input_template='scolar/certificat_pdf.html',
                                                               header_template=None,
                                                               footer_template=None,
                                                               context=context,
                                                               cmd_options=cmd_options)
                    email.attach(certificat_filename, certificat_pdf_, 'application/pdf')
                    cmd_options = {
                        'orientation': 'Portrait',
                        'page-size': 'A4',
                    }

                    fiche_filename = 'FICHE_INSCRIPTION' + str(inscription_) + '.pdf'
                    context['inscription_annee_precedente'] = inscription_annee_precedente_
                    fiche_pdf_ = render_pdf_from_template(input_template='scolar/fiche_inscription_pdf.html',
                                                          header_template=None,
                                                          footer_template=None,
                                                          context=context,
                                                          cmd_options=cmd_options)
                    email.attach(fiche_filename, fiche_pdf_, 'application/pdf')

                    if inscription_annee_precedente_:
                        cmd_options = {
                            'orientation': 'Landscape',
                            'page-size': 'A4',
                        }

                        context['inscription'] = inscription_annee_precedente_
                        releve_filename = 'RELEVE_ANNUEL_' + str(inscription_annee_precedente_).replace(' ',
                                                                                                        '_') + '.pdf'
                        releve_pdf_ = render_pdf_from_template(input_template='scolar/releve_notes_pdf.html',
                                                               header_template=None,
                                                               footer_template=None,
                                                               context=context,
                                                               cmd_options=cmd_options)
                        email.attach(releve_filename, releve_pdf_, 'application/pdf')

                    if settings.EMAIL_ENABLED:
                        email.send(fail_silently=True)

                    messages.success(request, "La préinscription a été validée avec succès!")
                else:
                    inscription_.preinscription.photo.delete()
                    inscription_.preinscription.quittance.delete()
                    Preinscription.objects.filter(inscription=inscription_).delete()
                    email = EmailMessage('Votre Inscription en ' + str(inscription_.formation),
                                         'Bonjour ' + inscription_.etudiant.prenom + ',\n' +
                                         "Votre inscription en : " + str(
                                             inscription_.formation) + ' n\'a pas été validée.\n'
                                                                       'Motif de refus:\n' +
                                         form_data['motif_refus'] + '\n' +
                                         'Bien cordialement.\n' +
                                         'Département', to=[inscription_.etudiant.user.email,
                                                            request.user.email] if not settings.DEBUG else [
                            'y_challal@esi.dz'])
                    if settings.EMAIL_ENABLED:
                        email.send(fail_silently=True)
                    messages.warning(request,
                                     "La préinscription n'a pas été validée! Une notification a été envoyée à l'étudiant pour compléter son dossier.")

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: lors de la validation de la préinscription. Merci de le signaler à l'administrateur.")

            # redirect to a new URL:
            # return HttpResponseRedirect(reverse('preinscription_list'))
            return HttpResponseRedirect(reverse('preinscription_list'))
    # if a GET (or any other method) we'll create a blank form
    else:
        form = ValidationPreInscriptionForm()
        context = {
            'form': form,
            'inscription': inscription_,
            'inscription_annee_precedente': inscription_annee_precedente_,
            'decision_jury': dict(DECISIONS_JURY),
            'titre': 'Validation de la Pré-Inscription de ' + str(inscription_)
        }

        messages.info(request, "Merci de vérifier ces informations avant de valider l'inscription.")
        messages.warning(request,
                         "Attention! Si une nouvelle photo est présente assurez vous qu'elle est semblable à l'ancienne. Sinon, refusez l'inscription.")
    return render(request, 'scolar/validation_preinscription.html', context)


class PVPFEPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/pv_pfe_pdf.html'
    cmd_options = {
        'orientation': 'Portrait',
        'page-size': 'A4',
    }

    def test_func(self):
        return self.request.user.is_stage() or self.request.user.is_direction()

    def get_context_data(self, **kwargs):
        context = super(PVPFEPDFView, self).get_context_data(**kwargs)
        groupe_ = Groupe.objects.get(id=self.kwargs.get('groupe_pk'))
        module_ = Module.objects.get(id=self.kwargs.get('module_pk'))
        self.filename = 'PV_' + str(groupe_.code)
        resultat_list = {}
        for resultat_ in Resultat.objects.filter(module=module_, resultat_ue__inscription_periode__groupe=groupe_):
            resultat_list[resultat_.inscription.etudiant.matricule] = resultat_
            self.filename += '_' + str(resultat_.inscription.etudiant.nom)
        self.filename += '.pdf'
        # Attention, si on télécharge le PV, on marque la saisie des notes comme terminée
        module_suivi_ = get_object_or_404(ModulesSuivis, groupe=groupe_, module=module_)
        module_suivi_.saisie_notes = 'T'
        module_suivi_.save()
        context['groupe'] = groupe_
        context['module'] = module_
        context['resultat_list'] = resultat_list
        context['date'] = datetime.date.today()
        context['mention'] = dict(MENTION)
        context['decision_jury'] = dict(DECISIONS_JURY)
        context['options_depot'] = dict(OPTIONS_DEPOT)
        return context


class ReleveNotesProvisoirePDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/releve_notes_provisoire_pdf.html'
    cmd_options = {
        'orientation': 'Landscape',
        'page-size': 'A4',
    }

    def test_func(self):
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        return self.request.user.is_staff_or_student_himself(inscription_.etudiant.matricule)

    def get_context_data(self, **kwargs):
        context = super(ReleveNotesProvisoirePDFView, self).get_context_data(**kwargs)
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        periode_ = PeriodeProgramme.objects.get(id=self.kwargs.get('periode_pk'))
        self.filename = str(inscription_) + '.pdf'
        context['inscription'] = inscription_
        context['periode'] = inscription_.inscription_periodes.all().get(periodepgm=periode_)
        context['date'] = datetime.date.today()
        context['categorie_ue'] = dict(CAT_UE)
        context['credits'] = 1 if inscription_.formation.programme.ordre <= 2 else None

        return context


class ReleveNotesProvisoireListPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/releve_notes_provisoire_list_pdf.html'
    cmd_options = {
        'orientation': 'Landscape',
        'page-size': 'A4',
    }

    def test_func(self):
        return self.request.user.is_scolarite() or self.request.user.is_direction()

    def get_context_data(self, **kwargs):
        context = super(ReleveNotesProvisoireListPDFView, self).get_context_data(**kwargs)
        formation_ = Formation.objects.get(id=self.kwargs.get('formation_pk'))
        periode_ = Periode.objects.get(id=self.kwargs.get('periode_pk'))
        inscription_periode_list = InscriptionPeriode.objects.filter(inscription__formation=formation_,
                                                                     periodepgm__periode=periode_).exclude(
            groupe__isnull=True).exclude(inscription__decision_jury='X')
        self.filename = 'RELEVES_PROVISOIRE_' + str(formation_) + '.pdf'
        context['inscription_periode_list'] = inscription_periode_list
        context['date'] = datetime.date.today()
        context['categorie_ue'] = dict(CAT_UE)
        context['credits'] = 1 if formation_.programme.ordre <= 2 else None

        return context


class ReleveECTSPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/releve_ects_pdf.html'
    cmd_options = {
        'orientation': 'Portrait',
        'page-size': 'A3',
    }

    def test_func(self):
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        return self.request.user.is_staff_or_student_himself(inscription_.etudiant.matricule)

    def get_context_data(self, **kwargs):
        context = super(ReleveECTSPDFView, self).get_context_data(**kwargs)
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        self.filename = str(inscription_.etudiant) + '_ECTS.pdf'

        context['inscription'] = inscription_
        context['date'] = datetime.date.today()
        return context


class ReleveECTSView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/releve_ects.html'

    def test_func(self):
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        return self.request.user.is_staff_or_student_himself(inscription_.etudiant.matricule)

    def get_context_data(self, **kwargs):
        context = super(ReleveECTSView, self).get_context_data(**kwargs)
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        context['inscription'] = inscription_

        return context


def import_deliberation_view(request, annee_univ_pk):
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportDeliberationForm(annee_univ_pk, request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            try:
                deliberation_file = request.FILES['file']
                dataset = Dataset()
                imported_data = dataset.load(deliberation_file.read().decode('utf-8'), format='csv')
                # la première ligne du fichier doit contenir des entêtes, au moins Matricule Nom, Prenom, MoyAn,Rang, Decision
                # insert imported_data in inscription table
                form_data = form.cleaned_data
                formation_ = form_data['formation']
                # initialiser les decisions_jury en cours à Non Inscrit
                Inscription.objects.filter(formation=formation_, decision_jury='C').update(decision_jury='X')
                t = threading.Thread(target=task_deliberation_import, args=[formation_, imported_data, request.user])
                t.setDaemon(True)
                t.start()

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: L'import du PV de délibération n'a pas réussit. Il doit y avoir un problème de format")
                    messages.info(request, "Indiquer le fichier .csv PV de délibération annuel.")
                    messages.info(request,
                                  "La première ligne du fichier doit comporter au moins les colonnes suivantes: Matricule, Nom, Prenom, Rang, Decision, MoyAn")
                    messages.info(request,
                                  "La colonne Decision doit correspondre à une des valeurs: Admis, Non Admis, Admis avec rachat, Maladie, Abandon, Redouble, Non Inscrit")
                    render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer les Délibérations'})
            # redirect to a new URL:
            messages.success(request,
                             "Votre demande d'import du PV de délibérations a été prise en compte. Une notification vous sera transmise aussitôt effectuée.")
            return HttpResponseRedirect(reverse('deliberation_detail', kwargs={'formation_pk': formation_.id, }))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportDeliberationForm(annee_univ_pk)
        messages.info(request, "Indiquer le fichier .csv PV de délibération annuel.")
        messages.info(request,
                      "La première ligne du fichier doit comporter au moins les colonnes suivantes: Matricule, Nom, Prenom, Rang, Decision, MoyAn")
        messages.info(request,
                      "La colonne Decision doit correspondre à une des valeurs: Admis, Non Admis, Admis avec rachat, Maladie, Abandon, Redouble, Non Inscrit")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer les Délibérations'})


@transaction.atomic
def task_deliberation_import(formation_, imported_data, user):
    try:
        for row in imported_data.dict:
            etudiant_, created = Etudiant.objects.get_or_create(matricule=row['Matricule'], defaults={
                'matricule': row['Matricule'],
                'nom': row['Nom'],
                'prenom': row['Prenom']
            })
            inscription_, created = Inscription.objects.get_or_create(etudiant=etudiant_, formation=formation_,
                                                                      defaults={
                                                                          'etudiant': etudiant_,
                                                                          'formation': formation_,
                                                                      })
            rang_ = int(row['Rang'])
            decision_ = row['Decision']
            if decision_ == 'Admis':
                decision_ = 'A'
            elif decision_ == 'Admis avec rachat':
                decision_ = 'AR'
            elif decision_ == 'Abandon':
                decision_ = 'F'
            elif decision_ == 'Redouble':
                decision_ = 'R'
            elif decision_ == 'Maladie':
                decision_ = 'M1'
            elif decision_ == 'Non Admis':
                decision_ = 'N'
            else:
                decision_ = 'X'
            try:
                inscription_.moy = decimal.Decimal(row['MoyAn'].replace(",", "."))
                # inscription_.moy_post_delib=inscription_.moy
            except Exception:
                inscription_.moy = inscription_.moyenne()
                # inscription_.moy_post_delib=inscription_.moy
            inscription_.rang = rang_
            inscription_.decision_jury = decision_
            # inscription_.save(update_fields=['moy','moy_post_delib', 'rang','decision_jury'])
            inscription_.save(update_fields=['moy', 'rang', 'decision_jury'])

            # indiquer les modules acquis et calculer les ECTS
            for resultat_ in Resultat.objects.filter(inscription=inscription_):
                resultat_.ects = resultat_.calcul_ects()
                # resultat_.ects_post_delib=resultat_.ects
                if resultat_.moy >= 10:
                    resultat_.acquis = True
                else:
                    resultat_.acquis = False
                resultat_.save(update_fields=['ects', 'acquis'])

        formation_.archive = True
        formation_.save(update_fields=['archive'])
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage(
                '[Talents] Erreur lors de l\importation du PV de délibération de la formation ' + str(formation_),
                'Bonjour,\n' +
                'Une erreur s\'est produite lors de l\'importation du PV de délibération de ' + str(formation_) + '\n' +
                'Veuillez vérifier les données et réessayer l\'importation \n' +
                'Bien cordialement.\n' +
                'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)

    email = EmailMessage(
        '[Talents] Confirmation de l\'importation du PV de délibération de la formation ' + str(formation_),
        'Bonjour,\n' +
        'L\'importation du PV de délibération de la formation ' + str(formation_) + ' a bien été effectuée \n' +
        'Nous vous en remercions \n' +
        'Bien cordialement.\n' +
        'Département', to=[user.email])
    if settings.EMAIL_ENABLED:
        email.send(fail_silently=True)


@login_required
def export_inscriptions(request, formation_pk):
    if not (request.user.is_scolarite() or request.user.is_direction()):
        messages.error(request, "Vous n'êtes pas autorisés à excéuter cette opération.")
        return redirect('/accounts/login/?next=%s' % request.path)

    try:
        # Create the HttpResponse object with the appropriate CSV header.
        formation_ = get_object_or_404(Formation, id=formation_pk)
        inscription_list = Inscription.objects.filter(formation=formation_).order_by('etudiant__nom',
                                                                                     'etudiant__prenom')
        header = ['Matricule', 'Email', 'Nom', 'Prenom', 'Groupe', 'Situation']
        sheet = Dataset()
        sheet.headers = header

        for inscription_ in inscription_list:
            row_ = []
            row_.append(inscription_.etudiant.matricule)
            row_.append(inscription_.etudiant.user.email)
            row_.append(inscription_.etudiant.nom)
            row_.append(inscription_.etudiant.prenom)
            row_.append(inscription_.groupe.code if inscription_.groupe else '')
            row_.append("Maladie" if inscription_.decision_jury.startswith('M') else dict(DECISIONS_JURY)[
                inscription_.decision_jury])
            sheet.append(row_)

        filename = 'LISTE_' + str(formation_) + '.xlsx'
        filename = filename.replace(' ', '_')

        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=' + filename + ";"
        response.write(sheet.xlsx)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: Il y a eu une erreur lors de l'export du fichier des notes. Merci de le signaler à l'administrateur.")
    return response


def affectation_groupe_view(request):
    if not (request.user.is_direction()):
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportAffectationForm(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            try:
                affectation_file = request.FILES['file']
                dataset = Dataset()
                imported_data = dataset.load(affectation_file.read().decode('utf-8'), format='csv')
                # la première ligne du fichier doit contenir des entêtes, au moins Matricule Groupe Nom Prenom
                # insert imported_data in inscription table
                form_data = form.cleaned_data
                formation_ = form_data['formation']
                t = threading.Thread(target=task_affectation_groupe_import,
                                     args=[formation_, imported_data, request.user])
                t.setDaemon(True)
                t.start()
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: L'import des affectations aux groupes n'a pas réussit. Veuillez vérifier le fichier et son format.")

                    return render(request, 'scolar/import.html',
                                  {'form': form, 'titre': 'Importer l\'affectation aux groupes'})

            messages.success(request,
                             "La demande d'affectation aux groupes est prise en compte. Vous recevrez une notification aussitôt effectuée!")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('etudiant_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportAffectationForm()
        messages.info(request,
                      "Indiquer le fichier .csv d'affectation aux groupes des étudiants inscrits dans la formation indiquée ci-dessous.")
        messages.info(request,
                      "La première ligne du fichier doit comporter au moins les colonnes suivantes: Matricule, Nom, Prenom, Groupe")
        messages.warning(request,
                         "Attention! Ne faites cette affectation qu'après avoir créé les sections et groupes et avoir indiqués pour chaque groupe les UE optionnelles.")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer l\'affectation aux groupes'})


@transaction.atomic
def task_affectation_groupe_import(formation_, imported_data, user):
    try:
        for row in imported_data.dict:
            etudiant_, created = Etudiant.objects.get_or_create(matricule=row['Matricule'], defaults={
                'matricule': row['Matricule'],
                'nom': row['NomEtud'],
                'prenom': row['Prenoms']
            })
            groupe_ = Groupe.objects.get(section__formation=formation_, code=row['Groupe'])
            inscription_, created = Inscription.objects.update_or_create(etudiant=etudiant_, formation=formation_,
                                                                         defaults={
                                                                             'etudiant': etudiant_,
                                                                             'formation': formation_,
                                                                             # TODO enlever l'affectatation au groupe dans inscription on le maintient pour legacy compatibility
                                                                             # On gère le groupe dans InscriptionPeriode
                                                                             'groupe': groupe_,
                                                                             # 'rang':0,
                                                                             # 'moy':0,
                                                                             # 'moy_post_delib':0,
                                                                         })
            # On crée les InscriptionPeriode et on l'affecte au même groupe dans les deux semestres
            for periode_ in formation_.programme.periodes.all():
                InscriptionPeriode.objects.update_or_create(inscription=inscription_, periodepgm=periode_, defaults={
                    'inscription': inscription_,
                    'periodepgm': periode_,
                    'groupe': groupe_
                })
            if inscription_.etudiant.user:
                email = EmailMessage('[Talents] Affectation au groupe ' + str(groupe_),
                                     'Bonjour, ' + inscription_.etudiant.nom + ' ' + inscription_.etudiant.prenom + '\n' +
                                     'Nous vous informons que vous avez été effecté au groupe ' + str(groupe_) + '\n' +
                                     'Bien cordialement.\n' +
                                     'Département', to=[inscription_.etudiant.user.email])
                if settings.EMAIL_ENABLED:
                    email.send(fail_silently=True)
        email = EmailMessage(
            '[Talents] Confirmation de l\'importation de l\'affectation aux groupes de la formation ' + str(formation_),
            'Bonjour,\n' +
            'L\'importation de l\'affectation aux groupes de la formation ' + str(
                formation_) + ' a bien été effectuée \n' +
            'Nous vous en remercions \n' +
            'Bien cordialement.\n' +
            'Département', to=[user.email])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)

    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage(
                '[Talents] Erreur lors de l\importation des affectations aux groupes de la formation ' + str(
                    formation_),
                'Bonjour,\n' +
                'Une erreur s\'est produite lors de l\'importation de l\affectation aux groupes de ' + str(
                    formation_) + '\n' +
                'Veuillez vérifier les données et réessayer l\'importation \n' +
                'Bien cordialement.\n' +
                'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)


def affectation_pfe_valide_view(request):
    if not request.user.is_stage():
        messages.error(request, "Vous n'avez pas les permissions pour exécuter cette opération.")
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportAffectationDiplomeForm(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            try:
                affectation_file = request.FILES['file']
                dataset = Dataset()
                imported_data = dataset.load(affectation_file.read().decode('utf-8'), format='csv')
                # la première ligne du fichier doit contenir des entêtes, au moins Matricule Groupe Nom Prenom
                # insert imported_data in inscription table
                form_data = form.cleaned_data
                diplome_ = form_data['diplome']
                # attention, il s'agit ici de la formation associé au groupe de PFE et non pas la formation d'inscription
                # elles peuvent être différentes dans le cas de PFE mixtes, car on crée une formation Mixte, mais chaque étudiant du binôme garde sa spécialité donc sa formation à laquelle il est déjà inscrit
                formation_ = form_data['formation']
                module_ = Module.objects.get(formation=formation_, matiere__pfe=True)
                for row in imported_data.dict:
                    pfe_ = get_object_or_404(PFE, id=int(row.get('ID')))
                    matricule_list = [inscription_.etudiant.matricule for inscription_ in pfe_.reserve_pour.all()]

                    for matricule_ in matricule_list:

                        default_section_, created = Section.objects.get_or_create(formation=formation_, code='A',
                                                                                  defaults={
                                                                                      'formation': formation_,
                                                                                      'code': 'A'
                                                                                  })

                        groupe_, created = Groupe.objects.get_or_create(section=default_section_, code=row['Groupe'],
                                                                        defaults={
                                                                            'code': row['Groupe'],
                                                                            'section': default_section_
                                                                        })

                        try:
                            # modifier le groupe de l'inscription à la formation du PFE (Ing ou Master)
                            inscription_ = Inscription.objects.get(etudiant__matricule=matricule_,
                                                                   formation__programme__diplome=diplome_,
                                                                   formation__annee_univ=formation_.annee_univ)
                            # inscription_.groupe=groupe_
                            # inscription_.save()
                            # modifier le groupe d'inscription du semestre
                            InscriptionPeriode.objects.update_or_create(inscription=inscription_,
                                                                        periodepgm__periode=module_.periode.periode,
                                                                        defaults={
                                                                            'inscription': inscription_,
                                                                            'periodepgm': module_.periode,
                                                                            'groupe': groupe_
                                                                        })
                        except:
                            messages.error(request, "Etudiant non inscrit, il faut d'abord l'inscrire: " + matricule_)
                            continue

                    if pfe_.coencadrants.exists():
                        encadrant_list = pfe_.coencadrants.all()
                        # encadrant_=encadrant_list[0]
                    elif module_.coordinateur:
                        pfe_.coencadrants.add(module_.coordinateur)
                        encadrant_list = [module_.coordinateur]
                    else:
                        messages.error(request, "Il faut désigner un coencadrant pour le PFE N°: " + str(pfe_.id))
                        continue
                    pfe_.groupe = groupe_
                    pfe_.save()

                    # on crée une activité d'encadrement ce qui va déclecnher l'insertion des charges et permettra la saisie des notes
                    # le PFE figurera ainsi dans Mes enseignements et les charges

                    config_charge_ = form_data['config_charge']
                    activite_, created = Activite.objects.update_or_create(type=config_charge_.type, module=module_,
                                                                           cible__in=[groupe_], defaults={
                            'type': config_charge_.type,
                            'module': module_,
                            'repeter_chaque_semaine': config_charge_.repeter_chaque_semaine,
                            'vh': config_charge_.vh,
                            'repartir_entre_intervenants': True,
                        })
                    activite_.cible.clear()
                    activite_.cible.add(groupe_)
                    for enseignant_ in activite_.assuree_par.all():
                        activite_.assuree_par.remove(enseignant_)
                    for enseignant in encadrant_list:
                        activite_.assuree_par.add(enseignant)
                    activite_.save()
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: L'affectation aux PFE n'a pas réussit. Le fichier est peut être mal formé!")
                    messages.info(request,
                                  "Indiquer le fichier .csv d'affectation aux PFE des étudiants inscrits dans la formation indiquée ci-dessous.")
                    messages.info(request,
                                  "La première ligne du fichier doit comporter au moins les colonnes suivantes: Groupe, ID,")
                    messages.info(request, "La colonne Groupe correspond au code PFE, par ex. PSL23.")
                    render(request, 'scolar/import.html', {'form': form, 'titre': 'Confirmer l\'affectation aux PFE'})
            messages.success(request, "L'affectation des étudiants aux PFE validés a été réalisée avec succès!")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('pfe_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportAffectationDiplomeForm()
        messages.info(request,
                      "Indiquer le fichier .csv d'affectation aux PFE des étudiants inscrits dans la formation indiquée ci-dessous.")
        messages.info(request,
                      "La première ligne du fichier doit comporter au moins les colonnes suivantes: Groupe, ID")
        messages.info(request, "La colonne Groupe correspond au code PFE, par ex. PSL23..")
        messages.warning(request,
                         "Assurez vous que tous les binômes suivent le même module. Pour les binômes mixtes il faut créer une formation Mixte")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Confirmer l\'affectation aux PFE'})


def affectation_pfe_view(request):
    if not request.user.is_stage():
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportAffectationDiplomeForm(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            try:
                affectation_file = request.FILES['file']
                dataset = Dataset()
                imported_data = dataset.load(affectation_file.read().decode('utf-8'), format='csv')
                # la première ligne du fichier doit contenir des entêtes, au moins Matricule Groupe Nom Prenom
                # insert imported_data in inscription table
                form_data = form.cleaned_data
                diplome_ = form_data['diplome']
                # attention, il s'agit ici de la formation associé au groupe de PFE et non pas la formation d'inscription
                # elles peuvent être différentes dans le cas de PFE mixtes, car on crée une formation Mixte, mais chaque étudiant du binôme garde sa spécialité donc sa formation à laquelle il est déjà inscrit
                formation_ = form_data['formation']
                module_ = Module.objects.get(formation=formation_, matiere__pfe=True)
                for row in imported_data.dict:
                    if row.get('Matricule'):
                        matricule_list = row['Matricule'].split('+')
                    else:
                        nom_list = row['Nom'].split('+')
                        prenom_list = row['Prenom'].split('+')
                        matricule_list = []
                        for nom_ in nom_list:
                            prenom_ = prenom_list[nom_list.index(nom_)]
                            try:
                                matricule_ = Etudiant.objects.get(nom__icontains=nom_,
                                                                  prenom__icontains=prenom_).matricule
                            except Exception:
                                messages.error(request,
                                               "L'étudiant " + nom_ + " " + prenom_ + " n'existe pas. Il faut corriger le nom ou l'insérer")
                                break
                            matricule_list.append(matricule_)

                    etudiant_list = []

                    for matricule_ in matricule_list:
                        etudiant_ = Etudiant.objects.get(matricule=matricule_)
                        etudiant_list.append(etudiant_)

                        default_section_, created = Section.objects.get_or_create(formation=formation_, code='A',
                                                                                  defaults={
                                                                                      'formation': formation_,
                                                                                      'code': 'A'
                                                                                  })

                        groupe_, created = Groupe.objects.get_or_create(section=default_section_, code=row['Groupe'],
                                                                        defaults={
                                                                            'code': row['Groupe'],
                                                                            'section': default_section_
                                                                        })

                        try:
                            # modifier le groupe de l'inscription à la formation du PFE (Ing ou Master)
                            inscription_ = Inscription.objects.get(etudiant=etudiant_,
                                                                   formation__programme__diplome=diplome_,
                                                                   formation__annee_univ=formation_.annee_univ)
                            # inscription_.groupe=groupe_
                            # inscription_.save()
                            # modifier le groupe d'inscription du semestre
                            InscriptionPeriode.objects.update_or_create(inscription=inscription_,
                                                                        periodepgm__periode=module_.periode.periode,
                                                                        defaults={
                                                                            'inscription': inscription_,
                                                                            'periodepgm': module_.periode,
                                                                            'groupe': groupe_
                                                                        })
                        except:
                            messages.error(request,
                                           "Etudiant non inscrit, il faut d'abord l'inscrire: " + str(etudiant_))
                            continue

                    if len(etudiant_list) == 0:
                        messages.error(request, "Au moins un étudiant n'est pas valide sur cette ligne")
                        continue

                    if row['CoEncadrants']:
                        encadrant_list = get_enseignant_list_from_str(row['CoEncadrants'])
                        # encadrant_=encadrant_list[0]
                    else:
                        messages.error(request,
                                       "La présence d'un Encdrant pour le PFE " + str(groupe_) + " est obligatoire.")
                        continue

                    pfe_, created = PFE.objects.update_or_create(groupe=groupe_, defaults={
                        'groupe': groupe_,
                        'intitule': row['Intitule'],
                        # 'encadrant':encadrant_,
                        'promoteur': row['Promoteur']
                    })
                    pfe_.coencadrants.clear()
                    for enseignant in encadrant_list:
                        pfe_.coencadrants.add(enseignant)
                    pfe_.save()

                    # on crée une activité d'encadrement ce qui va déclecnher l'insertion des charges et permettra la saisie des notes
                    # le PFE figurera ainsi dans Mes enseignements et les charges

                    config_charge_ = form_data['config_charge']
                    activite_, created = Activite.objects.update_or_create(type=config_charge_.type, module=module_,
                                                                           cible__in=[groupe_], defaults={
                            'type': config_charge_.type,
                            'module': module_,
                            'repeter_chaque_semaine': config_charge_.repeter_chaque_semaine,
                            'vh': config_charge_.vh,
                            'repartir_entre_intervenants': True,
                        })
                    activite_.cible.clear()
                    activite_.cible.add(groupe_)
                    for enseignant_ in activite_.assuree_par.all():
                        activite_.assuree_par.remove(enseignant_)
                    for enseignant in encadrant_list:
                        activite_.assuree_par.add(enseignant)
                    activite_.save()
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: L'affectation aux PFE n'a pas réussit. Le fichier est peut être mal formé!")
                    messages.info(request,
                                  "Indiquer le fichier .csv d'affectation aux PFE des étudiants inscrits dans la formation indiquée ci-dessous.")
                    messages.info(request,
                                  "La première ligne du fichier doit comporter au moins les colonnes suivantes: Matricule, Nom, Prenom, Groupe, Intitule, Promoteur, Encadrant")
                    messages.info(request, "La colonne Groupe correspond au code PFE, par ex. PSL23.")
                    render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer l\'affectation aux PFE'})
            messages.success(request, "L'affectation aux PFE a été réalisée avec succès!")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('pfe_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportAffectationDiplomeForm()
        messages.info(request,
                      "Indiquer le fichier .csv d'affectation aux PFE des étudiants inscrits dans la formation indiquée ci-dessous.")
        messages.info(request,
                      "La première ligne du fichier doit comporter au moins les colonnes suivantes: Matricule, Nom, Prenom, Groupe, Promoteur, Intitule, CoEncadrants")
        messages.info(request, "La colonne Groupe correspond au code PFE, par ex. PSL23..")
        messages.warning(request,
                         "Assurez vous que tous les binômes suivent le même module. Pour les binômes mixtes il faut créer une formation Mixte")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer l\'affectation aux PFE'})


@receiver(post_save, sender=InscriptionPeriode)
def add_resultat_inscription(sender, update_fields, instance, created, **kwargs):
    # créer les résultats que doit avoir l'étudiant
    if instance.groupe:
        # màj le groupe de Inscription avec le groupe de la dernière InscriptionPeriode <=> groupe actuel
        derniere_inscription_periode = instance.inscription.inscription_periodes.all().order_by(
            'periodepgm__periode__ordre').last()
        if derniere_inscription_periode == instance:
            instance.inscription.groupe = derniere_inscription_periode.groupe
            instance.inscription.save(update_fields=['groupe'])

        periode_ = instance.periodepgm
        modules_suivis_ = ModulesSuivis.objects.filter(groupe=instance.groupe)
        ue_list = []
        for ue_ in periode_.ues.filter(nature='OBL'):
            ue_list.append(ue_)
        for ue_ in instance.groupe.option.filter(periode=periode_):
            ue_list.append(ue_)
        for ue_ in ue_list:
            resultat_ue, created = ResultatUE.objects.get_or_create(inscription_periode=instance, ue=ue_, defaults={
                'inscription_periode': instance,
                'ue': ue_,
            })
            for matiere_ in ue_.matieres.all():
                resultat_, created = Resultat.objects.get_or_create(inscription=instance.inscription,
                                                                    module__matiere__code=matiere_.code, defaults={
                        'inscription': instance.inscription,
                        'resultat_ue': resultat_ue,
                        'module': modules_suivis_.get(module__matiere__code=matiere_.code).module,
                    })
                if created:
                    # Si module acquis alors copier l'ancien dans le nouveau
                    old_resultat_ = Resultat.objects.filter(inscription__etudiant=instance.inscription.etudiant,
                                                            module__matiere__code=matiere_.code,
                                                            inscription__decision_jury='R', acquis=True)
                    if old_resultat_.exists():
                        old_resultat_ = old_resultat_[0]
                        resultat_.moy = old_resultat_.moy
                        resultat_.moy_post_delib = old_resultat_.moy_post_delib
                        resultat_.ecst = old_resultat_.ects
                        # resultat_.ects_post_delib=old_resultat_.ects_post_delib
                        resultat_.acquis = True
                        resultat_.save(update_fields=['moy', 'moy_post_delib', 'ects', 'acquis'])
                else:
                    # ici on gère le cas d'un changement de groupe vers un groupe compatible (suivant les mêmes modules que
                    # l'ancien groupe, mais pour certaines matières elles sont suivies à des semestres différents
                    # ATTENTION: on ne gère pas bien le changement de groupe vers un groupe incompatible: on crée les nouveaux modules mais
                    # on ne supprime pas les anciens par peur de perdre des notes et résultats intermédiaires
                    resultat_.module = modules_suivis_.get(module__matiere=matiere_).module
                    resultat_.resultat_ue = resultat_ue
                    resultat_.save(update_fields=['module', 'resultat_ue'])


@receiver(post_save, sender=Note)
def update_resultat_moy(sender, update_fields, instance, created, **kwargs):
    resultat = get_object_or_404(Resultat, id=instance.resultat.id)
    if resultat.inscription.formation.archive != True:
        resultat.moy = resultat.moyenne()
        resultat.moy_post_delib = resultat.moy
        resultat.save(update_fields=['moy', 'moy_post_delib'])


def notes_module_import_view(request, module_pk, groupe_pk):
    module_ = get_object_or_404(Module, id=module_pk)
    groupe_ = get_object_or_404(Groupe, id=groupe_pk)

    if request.user.is_direction():
        pass
    elif module_.formation.archive or module_.pv_existe():
        messages.error(request, "La saisie des notes est clôturée pour cette formation.")
        return HttpResponseRedirect(
            reverse('note_list', kwargs={'groupe_pk': groupe_pk, 'matiere_pk': module_.matiere.id}))
    elif request.user.is_enseignant():
        if not assure_module(request.user.enseignant, module_):
            messages.error(request, "Vous n'êtes pas autorisés à accéder à cette fonction.")
            return redirect('/accounts/login/?next=%s' % request.path)
    else:
        messages.error(request, "Vous n'êtes pas autorisés à accéder à cette fonction.")
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = OTPImportFileForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            # Vérifier que l'OTP est correct
            if not settings.SMS_ENABLED or request.user.is_direction() or request.user.enseignant.check_otp(
                    form.cleaned_data['otp']):
                try:
                    notes_file = request.FILES['file']
                    dataset = Dataset()
                    imported_data = dataset.load(notes_file.read(), format='xlsx')
                    # insert imported_data in resultat table
                    t = threading.Thread(target=task_notes_module_import,
                                         args=[module_, groupe_, imported_data, request.user])
                    t.setDaemon(True)
                    t.start()
                except Exception:
                    if settings.DEBUG:
                        raise Exception
                    else:
                        messages.error(request,
                                       "ERREUR: L'import des notes n'a pas réussit. Il doit y avoir un problème de format du fichier.")
                        return HttpResponseRedirect(
                            reverse('note_list', kwargs={'groupe_pk': groupe_pk, 'matiere_pk': module_.matiere.id}))
                messages.info(request,
                              "Votre demande d'importation de notes a été prise en compte. Une notification vous sera transmise une fois la tâche terminée.")
            else:
                messages.error(request, "Le Mot de Passe à usage unique saisi est incorrect.")
        else:
            messages.error(request, "Le formulaire est incorrect.")
        # redirect to a new URL:
        return HttpResponseRedirect(
            reverse('note_list', kwargs={'groupe_pk': groupe_pk, 'matiere_pk': module_.matiere.id}))
        # if a GET (or any other method) we'll create a blank form
    else:
        if not request.user.enseignant.tel:
            messages.error(request,
                           "Votre numéro de téléphone n'est pas enregsitré dans la base. Il est nécessaire pour vous envoyer un Mot de passe à Usage Unique.")
            messages.info(request,
                          "Merci de communiquer votre numéro à l'administration afin que vous puissiez saisir les notes.")
            return HttpResponseRedirect(
                reverse('note_list', kwargs={'groupe_pk': groupe_pk, 'matiere_pk': module_.matiere.id}))
        else:
            # Génération et envoie de l'OTP pour sécuriser la saisie des notes
            url_ = settings.SMS_URL
            params_ = {
                'function': 'sms_send',
                'apikey': settings.SMS_API_KEY,
                'userkey': settings.SMS_USER_KEY,
                'message': 'Talents Code Secret: ' + request.user.enseignant.set_otp(),
                'message_priority': 'Urgent',
                'to': request.user.enseignant.tel
            }
            if settings.SMS_ENABLED and not request.user.is_direction():
                requests.get(url=url_, params=params_)

            form = OTPImportFileForm()
            messages.warning(request, "Nous avons transmis un code secret, à saisir, par SMS sur votre numéro.")
            messages.info(request,
                          "Indiquez le fichier .xlsx contenant les notes de " + str(module_.matiere.code) + ' ' + str(
                              groupe_.code))
            messages.info(request,
                          "La première ligne du fichier doit contenir au moins les colonnes: Matricule, et une colonne préfixée par Moy puis le code du module, ex. MoyALSDD, MoyURSI, etc.")
            #             return render(request, 'scolar/import_notes_form.html', {'form': form, 'titre':'Importer des notes', 'module_':module_, 'groupe_':groupe_,
            #                                                                      'sms':settings.SMS_ENABLED,
            #                                                                      'url':settings.SMS_URL,
            #                                                                      'function':'sms_send',
            #                                                                      'apikey':settings.SMS_API_KEY,
            #                                                                      'userkey':settings.SMS_USER_KEY,
            #                                                                      'message':'Talents Code Secret: '+request.user.enseignant.set_otp(),
            #                                                                      'to':request.user.enseignant.tel
            #                                                                      })
            return render(request, 'scolar/import_notes_form.html', {'form': form, 'titre': 'Importer des notes'})


@transaction.atomic
def task_notes_module_import(module_, groupe_, imported_data, user):
    try:
        evaluation_list = module_.evaluations.all()
        for row in imported_data.dict:

            etudiant_ = Etudiant.objects.get(matricule=row['Matricule'])

            # récupérer le résultat de l'étudiant correspondant au module
            non_modifie = ''
            try:
                resultat_ = get_object_or_404(Resultat, inscription__decision_jury='C', inscription__etudiant=etudiant_,
                                              module=module_)
            except Exception:
                non_modifie += str(etudiant_) + ' En situation d\'Abandon ou Maladie\n'
                continue
            else:
                if not resultat_.acquis:

                    for eval_ in evaluation_list:
                        try:
                            note_, created = Note.objects.update_or_create(evaluation=eval_, resultat=resultat_,
                                                                           defaults={
                                                                               'evaluation': eval_,
                                                                               'resultat': resultat_,
                                                                               'note': row.get(eval_.type) if row.get(
                                                                                   eval_.type) else 0
                                                                           })
                        except Exception:
                            non_modifie += str(etudiant_) + 'Note de ' + eval_.type + ' Incorrecte'
                            continue

                    if not evaluation_list.exists():
                        try:
                            if row.get('Moy' + module_.matiere.code):
                                resultat_.moy = round(row.get('Moy' + module_.matiere.code), 2)
                                resultat_.moy_post_delib = resultat_.moy
                                resultat_.save(update_fields=['moy', 'moy_post_delib'])
                        except Exception:
                            non_modifie += str(etudiant_) + 'Moy' + module_.matiere.code + ' Incorrecte'
                            continue

                else:
                    non_modifie += str(etudiant_) + ' Module déjà acquis\n'
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage('[Talents] Erreur lors de l\'enregistrement des notes de ' + str(module_),
                                 'Bonjour,\n' +
                                 'Une erreur s\'est produite lors de l\'enregistrement des notes de ' + str(
                                     module_) + '\n' +
                                 'Veuillez réessayer l\'importation \n' +
                                 'Bien cordialement.\n' +
                                 'Département',
                                 to=[user.email, module_.formation.programme.departement.responsable.user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)
    else:
        ModulesSuivis.objects.update_or_create(groupe=groupe_, module=module_, defaults={
            'groupe': groupe_,
            'module': module_,
            'saisie_notes': 'T'
        })
        if non_modifie != '':
            non_modifie = 'Les notes de ces étudiants n\'ont pas été modifiées:\n' + non_modifie
        email = EmailMessage(
            '[Talents] Confirmation de l\'enregistrement des notes de ' + str(module_.matiere.code) + ' ' + str(
                groupe_),
            'Bonjour,\n' +
            'L\'enregistrement des notes de ' + str(module_.matiere.code) + ' du groupe ' + str(
                groupe_) + ' a bien été effectué \n' +
            non_modifie +
            'Modification effectuée via le compte ' + user.email + '\n' +
            'Bien cordialement.\n' +
            'Département',
            to=[user.email, module_.formation.programme.departement.responsable.user.email] if not settings.DEBUG else
            settings.STAFF_EMAILS['webmaster'])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)


def notes_import_view(request):
    if not (request.user.is_direction()):
        messages.error(request, "Vous n'êtes pas autorisés à accéder à cette fonction.")
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportNotesForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            try:
                pv_file = request.FILES['file']
                dataset = Dataset()
                imported_data = dataset.load(pv_file.read().decode('utf-8'), format='csv')
                # insert imported_data in resultat table
                form_data = form.cleaned_data
                formation_ = form_data['formation']
                t = threading.Thread(target=task_notes_import, args=[formation_, imported_data, request.user])
                t.setDaemon(True)
                t.start()

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: L'import des notes n'a pas réussit. Il doit y avoir un problème de format du fichier.")
                    messages.info(request,
                                  "Indiquez le fichier .csv contenant les notes qui correspondent à la formation indiquée ci-dessous.")
                    messages.info(request,
                                  "La première ligne du fichier doit contenir au moins les colonnes: Matricule, et une colonne par matière, ex. ALSDD, URSI, etc.  préfixée par le terme Moy")

                    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des notes'})
            messages.info(request,
                          "Votre demande d'importation de notes a été prise en compte. Une notification vous sera transmise une fois la tâche terminée.")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('notes_formation_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportNotesForm()
        messages.info(request,
                      "Indiquez le fichier .csv contenant les notes qui correspondent à la formation indiquée ci-dessous.")
        messages.info(request,
                      "La première ligne du fichier doit contenir au moins les colonnes: Matricule, et une colonne par matière, ex. ALSDD, URSI, etc. préfixée par le terme Moy")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des notes'})


@transaction.atomic
def task_notes_import(formation_, imported_data, user):
    try:
        for row in imported_data.dict:
            etudiant_ = Etudiant.objects.get(matricule=row['Matricule'])
            inscription_ = Inscription.objects.get(etudiant=etudiant_, formation=formation_)
            # modules_suivis=ModulesSuivis.objects.filter(groupe=inscription_.groupe).values_list('module')
            # les resultats d'un étudiant sont déjà créés lors de son affectation à un groupe (on sait ce qu'il doit suivre
            for resultat_ in Resultat.objects.filter(inscription=inscription_):  # , module__in=modules_suivis
                # on tente de récupérer la note du module du fichier excel
                moy_ = row.get('Moy' + resultat_.module.matiere.code)
                # si une telle colonne existe dans le fichier excel alors on récupère la moyenne
                if moy_:
                    resultat_.moy = decimal.Decimal(moy_.replace(",", "."))
                    resultat_.moy_post_delib = resultat_.moy
                    resultat_.save(update_fields=['moy', 'moy_post_delib'])
            # traiter le cas particulier du PFE
            mention_ = row.get('Mention')
            if mention_:
                inscription_.mention = mention_
                inscription_.moy = decimal.Decimal(row.get('PFE').replace(",", "."))
                if inscription_.moy >= 10.0:
                    inscription_.decision_jury = 'A'
                inscription_.save(update_fields=['mention', 'moy', 'decision_jury'])
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage('[Talents] Erreur lors de l\'enregistrement des notes de ' + str(formation_),
                                 'Bonjour,\n' +
                                 'Une erreur s\'est produite lors de l\'enregistrement des notes de ' + str(
                                     formation_) + '\n' +
                                 'Veuillez réessayer l\'importation \n' +
                                 'Bien cordialement.\n' +
                                 'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)

    email = EmailMessage('[Talents] Confirmation de l\'enregistrement des notes de ' + str(formation_),
                         'Bonjour,\n' +
                         'L\'importation des notes de ' + str(formation_) + ' a bien été effectuée \n' +
                         'Nous vous en remercions \n' +
                         'Bien cordialement.\n' +
                         'Département', to=[user.email])
    if settings.EMAIL_ENABLED:
        email.send(fail_silently=True)


class SettingsDetailView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/settings.html'
    success_message = "Utilisez cette page pour configurer Talents"

    def test_func(self):
        return self.request.user.is_direction()

    def get_context_data(self, **kwargs):
        context = super(SettingsDetailView, self).get_context_data(**kwargs)

        table = ActiviteChargeConfigTable(ActiviteChargeConfig.objects.all().order_by('type'),
                                          exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)

        context['activite_charge_config_table'] = table

        context['titre'] = 'Paramètres de Talents'
        table = ResidenceUnivTable(ResidenceUniv.objects.all().order_by('nom'),
                                   exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)

        context['residence_univ_table'] = table

        qs = Institution.objects.all()

        if len(qs) > 0:
            institution_ = qs[0]
        else:
            institution_ = Institution.objects.create(nom='Aucune Institution', sigle='Absent')
        context['form'] = InstitutionDetailForm(instance=institution_)
        context['institution'] = institution_

        return context


class SettingsUpdateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, UpdateView):
    model = Institution
    fields = ['nom', 'nom_a', 'sigle', 'adresse', 'ville', 'tel', 'fax', 'web', 'illustration_cursus', 'banniere',
              'logo', 'logo_bis', 'header', 'footer']
    template_name = 'scolar/settings.html'
    success_message = "Utilisez cette page pour configurer Talents"

    def test_func(self):
        return self.request.user.is_direction()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        #         form.fields['illustration_cursus']=forms.ImageField(label='Illustration du cursus', required=False, widget=forms.FileInput(attrs={'class':"custom-file-input"}))
        #         form.fields['banniere']=forms.ImageField(label='Banniere', required=False, widget=forms.FileInput(attrs={'class':"custom-file-input"}))
        #         form.fields['logo']=forms.ImageField(label='Logo', required=False, widget=forms.FileInput(attrs={'class':"custom-file-input"}))
        #         form.fields['logo_bis']=forms.ImageField(label='Logo bis', required=False, widget=forms.FileInput(attrs={'class':"custom-file-input"}))
        #         form.fields['header']=forms.ImageField(label='Entête', required=False, widget=forms.FileInput(attrs={'class':"custom-file-input"}))
        #         form.fields['footer']=forms.ImageField(label='Pied de page', required=False, widget=forms.FileInput(attrs={'class':"custom-file-input"}))
        form.helper.add_input(Submit('submit', 'Enregistrer', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('settings')
        return form

    def get_context_data(self, **kwargs):
        context = super(SettingsUpdateView, self).get_context_data(**kwargs)

        table = ActiviteChargeConfigTable(ActiviteChargeConfig.objects.all().order_by('type'),
                                          exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)

        context['activite_charge_config_table'] = table

        table = ResidenceUnivTable(ResidenceUniv.objects.all().order_by('nom'),
                                   exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)

        context['residence_univ_table'] = table

        context['titre'] = 'Paramètres de Talents'

        return context


def organismes_import_view(request):
    if not (request.user.is_stage() or request.user.is_direction()):
        messages.error(request, "Vous n'avez pas les permissions d'accès à cette opération")
        return redirect('/accounts/login/?next=%s' % request.path)
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportFileForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            try:
                organismes_file = request.FILES['file']
                dataset = Dataset(
                    headers=['SIGLE', 'NOM', 'ADRESSE', 'PAYS', 'TYPE', 'NATURE', 'STATUT', 'SECTEUR', 'TAILLE'])
                imported_data = dataset.load(organismes_file.read().decode('utf-8'), format='csv')
                # insert imported_data in Organisme table
                lignes_problemes = []
                for row in imported_data.dict:
                    try:
                        organisme_, created = Organisme.objects.update_or_create(sigle=row['SIGLE'], defaults={
                            'sigle': row['SIGLE'],
                            'nom': row['NOM'],
                            'adresse': row['ADRESSE'],
                            'pays': get_object_or_404(Pays, code=row['PAYS']),
                            'type': row['TYPE'],
                            'nature': row['NATURE'],
                            'statut': row['STATUT'],
                            'secteur': row['SECTEUR'],
                            'taille': str(row['TAILLE'])
                        })
                    except Exception:
                        lignes_problemes.append(row['sigle'])
                        continue
                    # vérifier que le nom est identique à l'existant
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "L'importation du fichier des organisme n'a pas réussit. Il doit y avoir un problème de format du fichier.")
                    return render(request, 'scolar/import.html',
                                  {'form': form, 'titre': 'Importer des Organismes d\'accueil en Stage'})
            # redirect to a new URL:
            messages.success(request, "L'importation du fichier des Organismes s'est faite avec succès!")
            if len(lignes_problemes) > 0:
                messages.warning(request, "Ces organismes n'ont pu être importées")
                for pb in lignes_problemes:
                    messages.warning(request, pb)
            return HttpResponseRedirect(reverse('organisme_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportFileForm()
        messages.info(request, "Indiquer un fichier .csv des Organismes à importer dans la base de ESI Talents.")
        messages.info(request,
                      "le fichier doit avoir comme entête les colonnes suivantes: SIGLE, NOM, ADRESSE, PAYS, TYPE, NATURE, STATUT, SECTEUR, TAILLE")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des Organismes'})


def pays_import_view(request):
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportFileForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            try:
                pays_file = request.FILES['file']
                dataset = Dataset(headers=['code', 'nom'])
                imported_data = dataset.load(pays_file.read().decode('utf-8'), format='csv')
                # insert imported_data in Wilaya table
                lignes_problemes = []
                for row in imported_data.dict:
                    try:
                        pays_, created = Pays.objects.update_or_create(code=row['code'], defaults={
                            'code': row['code'],
                            'nom': row['nom']
                        })
                    except Exception:
                        lignes_problemes.append(row['code'])
                        continue
                    # vérifier que le nom est identique à l'existant
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "L'importation du fichier des pays n'a pas réussit. Il doit y avoir un problème de format du fichier.")
                    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des Pays'})
            # redirect to a new URL:
            messages.success(request, "L'importation du fichier des Pays s'est faite avec succès!")
            if len(lignes_problemes) > 0:
                messages.warning(request, "Ces Pays n'ont pu être importées")
                for pb in lignes_problemes:
                    messages.warning(request, pb)
            return HttpResponseRedirect(reverse('settings'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportFileForm()
        messages.info(request, "Indiquer un fichier .csv des Pays à importer dans la base de ESI Talents.")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des Pays'})


def wilayas_import_view(request):
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportFileForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            try:
                wilaya_file = request.FILES['file']
                dataset = Dataset(headers=['code', 'nom'])
                imported_data = dataset.load(wilaya_file.read().decode('utf-8'), format='csv')
                # insert imported_data in Wilaya table
                lignes_problemes = []
                for row in imported_data.dict:
                    try:
                        wilaya_, created = Wilaya.objects.update_or_create(code=row['code'], defaults={
                            'code': row['code'],
                            'nom': row['nom']
                        })
                    except Exception:
                        lignes_problemes.append(row['code'])
                        continue
                    # vérifier que le nom est identique à l'existant
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "L'importation du fichier des wilayas n'a pas réussit. Il doit y avoir un problème de format du fichier.")
                    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des Wilayas'})
            # redirect to a new URL:
            messages.success(request, "L'importation du fichier des Wilayas s'est faite avec succès!")
            if len(lignes_problemes) > 0:
                messages.warning(request, "Ces Wilayas n'ont pu être importées")
                for pb in lignes_problemes:
                    messages.warning(request, pb)
            return HttpResponseRedirect(reverse('settings'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportFileForm()
        messages.info(request, "Indiquer un fichier .csv des Wilayas à importer dans la base de ESI Talents.")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des Wilayas'})


def communes_import_view(request):
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportFileForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            try:
                commune_file = request.FILES['file']
                dataset = Dataset(headers=['code_postal', 'nom', 'wilaya'])
                imported_data = dataset.load(commune_file.read().decode('utf-8'), format='csv')
                # insert imported_data in Wilaya table
                lignes_problemes = []
                for row in imported_data.dict:
                    try:
                        commune_, created = Commune.objects.update_or_create(code_postal=row['code_postal'], defaults={
                            'code_postal': row['code_postal'],
                            'nom': row['nom'],
                            'wilaya': Wilaya.objects.get(code=row['wilaya'])
                        })
                    except Exception:
                        lignes_problemes.append(row['code_postal'])
                        continue
                    # vérifier que le nom est identique à l'existant
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "L'importation du fichier des communes n'a pas réussit. Il doit y avoir un problème de format du fichier.")
                    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des Commune'})
            # redirect to a new URL:
            messages.success(request, "L'importation du fichier des Comunes s'est faite avec succès!")
            if len(lignes_problemes) > 0:
                messages.warning(request, "Ces Commune n'ont pu être importées")
                for pb in lignes_problemes:
                    messages.warning(request, pb)
            return HttpResponseRedirect(reverse('settings'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportFileForm()
        messages.info(request, "Indiquer un fichier .csv des Communes à importer dans la base de ESI Talents.")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des Communes'})


def etudiants_import_maj_view(request):
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportFileForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            try:
                etudiant_file = request.FILES['file']
                dataset = Dataset(headers=['Matricule', 'NomEtud', 'Prenoms', 'Ddn',
                                           'LieuNaissance', 'WilayaNaissance', 'NomEtudA', 'PrenomsA', 'LieuNaissanceA',
                                           'Telephone', 'AdressePrincipale', 'WilayaResidence', 'CommuneResidence',
                                           'Interne', 'ResidenceU'])
                imported_data = dataset.load(etudiant_file.read().decode('utf-8'), format='csv')
                # insert imported_data in Etudiant table
                lignes_problemes = []
                for row in imported_data.dict:
                    try:
                        etudiant_ = Etudiant.objects.get(matricule=row['Matricule'])
                    except Exception:
                        lignes_problemes.append(row['Matricule'] + ' Indexistant')
                        continue
                    # vérifier que le nom est identique à l'existant
                    new_nom = row['NomEtud']
                    new_Ddn = datetime.datetime.strptime(row['Ddn'], '%Y-%m-%d').date()

                    if etudiant_.date_naissance == new_Ddn and etudiant_.nom.lower().replace(' ',
                                                                                             '') == new_nom.lower().replace(
                            ' ', ''):
                        # mettre à jour le dossier étudiant avec les infos
                        Etudiant.objects.filter(matricule=row['Matricule']).update(
                            nom=row['NomEtud'].upper(),
                            nom_a=row['NomEtudA'] if row['NomEtudA'] != '' else etudiant_.nom_a,
                            prenom=row['Prenoms'].upper() if row['Prenoms'] != '' else etudiant_.prenom.upper(),
                            prenom_a=row['PrenomsA'] if row['PrenomsA'] != '' else etudiant_.prenom_a,
                            lieu_naissance=row['LieuNaissance'].upper() if row[
                                                                               'LieuNaissance'] != '' else etudiant_.lieu_naissance.upper(),
                            lieu_naissance_a=row['LieuNaissanceA'] if row[
                                                                          'LieuNaissanceA'] != '' else etudiant_.lieu_naissance_a,
                            wilaya_naissance=Wilaya.objects.get(code=row['WilayaNaissance'].split()[0]),
                            tel=row['Telephone'],
                            addresse_principale=row['AddressePrincipale'].upper(),
                            wilaya_residence=Wilaya.objects.get(code=row['WilayaResidence'].split()[0]),
                            commune_residence=Commune.objects.get(code_postal=row['CommuneResidence'].split().pop()),
                            interne=True if row['Interne'] == "Oui" else False,
                            residence_univ=row['ResidenceU'].upper()
                        )
                    else:
                        lignes_problemes.append(row['Matricule'] + ' Noms ou Ddn différents.')
                        continue
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "L'importation du fichier des étudiants n'a pas réussit. Il doit y avoir un problème de format du fichier.")
                    messages.info(
                        "La première ligne du fichier .csv doit comprendre au moins les colonnes: 'Matricule','NomEtud', 'Prenoms', 'Ddn'," +
                        "'LieuNaissance', 'WilayaNaissance', 'NomEtudA', 'PrenomsA', 'LieuNaissanceA'," +
                        "'Telephone', 'AdressePrincipale', 'WilayaResidence', 'CommuneResidence'," +
                        "'Interne', 'ResidenceU'")
                    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des étudiants'})
            # redirect to a new URL:
            messages.success(request, "L'importatation du fichier des étudiants s'est faite avec succès!")
            if len(lignes_problemes) > 0:
                messages.warning(request, "Ces étudiants n'ont pu être importé")
                for pb in lignes_problemes:
                    messages.warning(request, pb)
            return HttpResponseRedirect(reverse('etudiant_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportFileForm()
        messages.info(request, "Indiquer un fichier .csv des étudiants à importer dans la base de ESI Talents.")
        messages.info(request,
                      "La première ligne du fichier .csv doit comprendre au moins les colonnes: 'Matricule','NomEtud', 'Prenoms', 'Ddn'," +
                      "'LieuNaissance', 'WilayaNaissance', 'NomEtudA', 'PrenomsA', 'LieuNaissanceA'," +
                      "'Telephone', 'AdressePrincipale', 'WilayaResidence', 'CommuneResidence'," +
                      "'Interne', 'ResidenceU'")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des étudiants'})


def etudiants_import_view(request):
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportFileForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            try:
                etudiant_file = request.FILES['file']
                dataset = Dataset(headers=['Matricule', 'NomEtud', 'Prenoms', 'Genre', 'Ddn',
                                           'LieuNaissance', 'WilayaNaissance', 'NomEtudA', 'PrenomsA', 'LieuNaissanceA',
                                           'Email', 'Telephone', 'AdressePrincipale', 'WilayaResidence',
                                           'CommuneResidence',
                                           'Interne', 'ResidenceU'])
                imported_data = dataset.load(etudiant_file.read().decode('utf-8'), format='csv')
                # insert imported_data in Etudiant table
                group = Group.objects.get(name='etudiant')
                lignes_pb = ''
                for row in imported_data.dict:
                    try:
                        wilaya_naissance_ = None
                        if row['WilayaNaissance'].isdigit() and Wilaya.objects.filter(
                                code=row['WilayaNaissance']).exists():
                            wilaya_naissance_ = Wilaya.objects.filter(code=row['WilayaNaissance'])[0]
                        elif Wilaya.objects.filter(nom__icontains=row['WilayaNaissance']).exists():
                            wilaya_naissance_ = Wilaya.objects.filter(nom__icontains=row['WilayaNaissance'])[0]

                        wilaya_residence_ = None
                        if row['WilayaResidence'].isdigit() and Wilaya.objects.filter(
                                code=row['WilayaResidence']).exists():
                            wilaya_residence_ = Wilaya.objects.filter(code=row['WilayaResidence'])[0]
                        elif Wilaya.objects.filter(nom__icontains=row['WilayaResidence']).exists():
                            wilaya_residence_ = Wilaya.objects.filter(nom__icontains=row['WilayaResidence'])[0]

                        etudiant_, created = Etudiant.objects.update_or_create(matricule=row['Matricule'], defaults={
                            'matricule': row['Matricule'],
                            'nom': row['NomEtud'].upper(),
                            'prenom': row['Prenoms'].upper(),
                            'sexe': row['Genre'],
                            'date_naissance': datetime.datetime.strptime(row['Ddn'], '%d/%m/%Y') if row[
                                'Ddn'] else None,
                            'lieu_naissance': row['LieuNaissance'].upper(),
                            'nom_a': row['NomEtudA'],
                            'prenom_a': row['PrenomsA'],
                            'lieu_naissance_a': row['LieuNaissanceA'],
                            'wilaya_naissance': wilaya_naissance_,
                            'tel': row['Telephone'],
                            'addresse_principale': row['AdressePrincipale'].upper(),
                            'wilaya_residence': wilaya_residence_,
                            'commune_residence': Commune.objects.filter(code_postal=row['CommuneResidence'])[
                                0] if Commune.objects.filter(code_postal=row['CommuneResidence']).exists() else None,
                            'interne': True if row['Interne'] == "Oui" else False,
                            'residence_univ': row['ResidenceU'].upper()
                        }
                                                                               )
                        if created:
                            psw = User.objects.make_random_password()
                            user = User.objects.create_user(row['Email'], row['Email'], psw)
                            user.groups.add(group)
                            user.save()
                            etudiant_.user = user
                            imagefilename = etudiant_.photo.field.upload_to
                            if default_storage.exists(
                                    settings.MEDIA_ROOT + '/' + etudiant_.photo.field.upload_to + '/' + etudiant_.matricule.replace(
                                            '/', '-') + '.jpg'):
                                imagefilename += '/' + etudiant_.matricule.replace('/', '-') + '.jpg'
                            else:
                                imagefilename += '/' + 'anonymous-user.jpg'

                            etudiant_.photo.name = imagefilename
                            etudiant_.save()
                    except Exception:
                        lignes_pb += row['Matricule'] + '\n'
                        continue
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "L'importation du fichier des étudiants n'a pas réussit. Il doit y avoir un problème de format du fichier.")
                    messages.info(request,
                                  "La première ligne du fichier .csv doit comprendre au moins les colonnes: 'Matricule','NomEtud', 'Prenoms', 'Ddn'," +
                                  "'LieuNaissance', 'WilayaNaissance', 'NomEtudA', 'PrenomsA', 'LieuNaissanceA'," +
                                  "'Telephone', 'AdressePrincipale', 'WilayaResidence', 'CommuneResidence'," +
                                  "'Interne', 'ResidenceU'")
                    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des étudiants'})
            # redirect to a new URL:
            messages.success(request, "L'importation du fichier des étudiants s'est faite avec succès!")
            if lignes_pb != '':
                messages.warning(request, "Les lignes suivantes n'ont pas été insérées à cause d'erreurs:\n" +
                                 lignes_pb)
            return HttpResponseRedirect(reverse('etudiant_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportFileForm()
        messages.info(request, "Indiquer un fichier .csv des étudiants à importer dans la base de ESI Talents.")
        messages.info(request,
                      "La première ligne du fichier .csv doit comprendre au moins les colonnes: 'Matricule','NomEtud', 'Prenoms', 'Ddn'," +
                      "'LieuNaissance', 'WilayaNaissance', 'NomEtudA', 'PrenomsA', 'LieuNaissanceA'," +
                      "'Telephone', 'AdressePrincipale', 'WilayaResidence', 'CommuneResidence'," +
                      "'Interne', 'ResidenceU'")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des étudiants'})


def inscriptions_import_view(request):
    if not (request.user.is_direction()):
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportFileForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            try:
                inscription_file = request.FILES['file']
                dataset = Dataset(headers=['Matricule', 'NomEtud', 'Prenoms', 'AnScol', 'Promo'])
                imported_data = dataset.load(inscription_file.read().decode('utf-8'), format='csv')
                # insert imported_data in Etudiant table
                group = Group.objects.get(name='etudiant')
                for row in imported_data.dict:
                    etudiant_, created = Etudiant.objects.get_or_create(matricule=row['Matricule'], defaults={
                        'matricule': row['Matricule'],
                        'nom': row['NomEtud'],
                        'prenom': row['Prenoms'],
                    }
                                                                        )
                    # Inscription de l'étudiant
                    annee_univ_, created = AnneeUniv.objects.get_or_create(annee_univ=row['AnScol'], defaults={
                        'annee_univ': row['AnScol']
                    })
                    programme_ = get_object_or_404(Programme, code=row['Promo'])
                    formation_, created = Formation.objects.get_or_create(programme=programme_, annee_univ=annee_univ_,
                                                                          defaults={
                                                                              'programme': programme_,
                                                                              'annee_univ': annee_univ_
                                                                          })
                    inscription_, created = Inscription.objects.update_or_create(etudiant=etudiant_,
                                                                                 formation=formation_, defaults={
                            'etudiant': etudiant_,
                            'formation': formation_,
                        })
                    # créer inscription_periodes selon le programme
                    for periode_ in formation_.programme.periodes.all():
                        InscriptionPeriode.objects.update_or_create(inscription=inscription_, periodepgm=periode_,
                                                                    defaults={
                                                                        'inscription': inscription_,
                                                                        'periodepgm': periode_,
                                                                    })

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: Echec de l'importation des inscriptions.")
                    messages.info(request,
                                  "La première ligne du fichier .csv doit comprendre au moins les colonnes: 'Matricule','NomEtud', 'Prenoms', 'AnScol', 'Promo'")
                    messages.info(request, "La colonne AnScol indique l'année universitaire, par ex. 2019")
                    messages.info(request,
                                  "La colonne Promo doit correspondre à une des promo 1CP, 2CP, 1CS, 2SL, 2SQ, 2ST, 3SL, 3ST, 3SQ, MSL, MST, MSQ")
                    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des inscriptions'})
            # redirect to a new URL:
            messages.success(request, "L'importation des inscriptions s'est faite avec succès!")
            return HttpResponseRedirect(reverse('inscription_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportFileForm()
        messages.info(request, "Indiquer un fichier .csv des inscriptions à importer dans la base de ESI Talents.")
        messages.info(request,
                      "La première ligne du fichier .csv doit comprendre au moins les colonnes: 'Matricule','NomEtud', 'Prenoms', 'AnScol', 'Promo'")
        messages.info(request, "La colonne AnScol indique l'année universitaire, par ex. 2019")
        messages.info(request,
                      "La colonne Promo doit correspondre à une des promo 1CP, 2CP, 1CS, 2SL, 2SQ, 2ST, 3SL, 3ST, 3SQ, MSL, MSQ, MST")

    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des inscriptions'})


@login_required
def enseignants_import_view(request):
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportFileForm(request.POST, request.FILES)

        # check whether it's valid:
        if form.is_valid():
            try:
                enseignant_file = request.FILES['file']
                dataset = Dataset(
                    headers=['Nom', 'Eps', 'Prenom', 'NomA', 'EpsA', 'PrenomA', 'Sexe', 'Grade', 'Situation', 'Tel',
                             'Bureau', 'Bal', 'Email', 'Charge'])
                imported_data = dataset.load(enseignant_file.read().decode('utf-8'), format='csv')
                # insert imported_data in Enseignant table
                group = Group.objects.get(name='enseignant')
                for row in imported_data.dict:
                    enseignant_, created = Enseignant.objects.update_or_create(user__email=row['Email'], defaults={
                        'nom': row['Nom'],
                        'eps': row['Eps'],
                        'prenom': row['Prenom'],
                        'nom_a': row['NomA'],
                        'eps_a': row['EpsA'],
                        'prenom_a': row['PrenomA'],
                        'sexe': row['Sexe'],
                        'grade': row['Grade'],
                        'situation': row['Situation'],
                        'bureau': row['Bureau'],
                        'tel': row['Tel'],
                        'bal': int(row['Bal']) if row['Bal'] != '' else 0,
                        'charge_statut': int(row['Charge']) if row['Charge'] != '' else 0

                    }
                                                                               )
                    if created:
                        psw = User.objects.make_random_password()
                        user = User.objects.create_user(row['Email'], row['Email'], psw)
                        user.groups.add(group)
                        user.save()
                        enseignant_.user = user
                        enseignant_.edt = '<iframe src="https://calendar.google.com/calendar/embed?src=' + user.email + '&ctz=Africa%2FAlgiers" style="border: 0" width="800" height="600" frameborder="0" scrolling="no"></iframe>'
                        enseignant_.save()
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: l'importation du fichier des enseignants s'est arrêtée avec echec.")
                    messages.info(request,
                                  "La première ligne doit comporter au moins les colonnes suivantes: 'Nom', 'Eps', 'Prenom', 'NomA', 'EpsA', 'PrenomA', 'Sexe', 'Grade', 'Situation', 'Tel', 'Bureau', 'Bal', 'Email', 'Charge'")
                    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des enseignants'})
            # redirect to a new URL:
            messages.success(request, "L'importation du fichier des enseignants s'est faite avec succès!")
            return HttpResponseRedirect(reverse('enseignant_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportFileForm()
        messages.info(request, "Indiquer le fichier .csv des enseignants.")
        messages.info(request,
                      "La première ligne doit comporter au moins les colonnes suivantes: 'Nom', 'Eps', 'Prenom', 'NomA', 'EpsA', 'PrenomA', 'Sexe', 'Grade', 'Situation', 'Tel', 'Bureau', 'Bal', 'Email', 'Charge'")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des enseignants'})


def feedback_import_view(request, module_pk):
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportFeedbackForm(module_pk, request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            try:
                feedback_file = request.FILES['file']

                dataset = Dataset()
                imported_data = dataset.load(feedback_file.read().decode('utf-8'), format='csv')
                # insert imported_data in Feebdback table
                form_data = form.cleaned_data
                module_ = form_data['module']

                for row in imported_data.dict:

                    feedback_ = Feedback.objects.create(module=module_)
                    for question_ in Question.objects.all():
                        if row.get(question_.code):
                            reponse_ = Reponse.objects.create(feedback=feedback_, question=question_)
                            reponse_.reponse = row[question_.code]
                            reponse_.save()
                    feedback_.comment = row['Comment']
                    feedback_.show = False
                    feedback_.save()
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: L'importation des feedbacks s'est terminée avec echec!")
                    messages.info(request,
                                  "La première ligne du fichier .csv doit comprendre les colonnes: Q01, Q02, Q03, ... Q10, Comment")
                    messages.info(request, "Les cellules comprennent les évaluations sous la forme de ++, +, -, --")
                    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des feedbacks'})
            # redirect to a new URL:
            messages.success(request, "L'importation des feedback s'est faite avec succès!")
            return HttpResponseRedirect(reverse('module_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportFeedbackForm(module_pk)
        messages.info(request, "Indiquer le fichier .csv contenant les évaluations du module indiqué ci-dessous.")
        messages.info(request,
                      "La première ligne du fichier .csv doit comprendre les colonnes: Q01, Q02, Q03, ... Q10, Comment")
        messages.info(request, "Les cellules comprennent les évaluations sous la forme de ++, +, -, --")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des feedbacks'})


class FeedbackChart(Chart):
    chart_type = 'bar'
    options = {
        'scales': {
            'xAxes': [{
                'stacked': True
            }],
            'yAxes': [{
                'stacked': True,
                'ticks': {
                    'suggestedMin': 0.0,
                    'suggestedMax': 1.0
                },
                'offset': True
            }]
        }
    }

    def __init__(self, module_pk, *args, **kwargs):
        super(FeedbackChart, self).__init__(*args, **kwargs)
        self.labels = []
        self.data = []
        try:
            self.module_ = get_object_or_404(Module, id=module_pk)
            feedback_list = Reponse.objects.filter(feedback__module=self.module_).exclude(reponse='')
            very_good_count = Count('reponse', filter=Q(reponse='++'))
            good_count = Count('reponse', filter=Q(reponse='+'))
            bad_count = Count('reponse', filter=Q(reponse='-'))
            very_bad_count = Count('reponse', filter=Q(reponse='--'))

            total_count = Count('reponse')
            feedback_data = feedback_list.values('feedback__module', 'question__code').order_by(
                'question__code').annotate(very_good=very_good_count).annotate(good=good_count).annotate(
                bad=bad_count).annotate(very_bad=very_bad_count).annotate(total=total_count)

            reponse_list = [
                {
                    'label': 'very_bad',
                    'reponse': '--',
                    'color': (256, 0, 0)
                },
                {
                    'label': 'bad',
                    'reponse': '-',
                    'color': (256, 256, 0)
                },
                {
                    'label': 'good',
                    'reponse': '+',
                    'color': (0, 256, 0)
                },
                {
                    'label': 'very_good',
                    'reponse': '++',
                    'color': (0, 128, 0)
                }

            ]

            for reponse in reponse_list:
                data_ = []
                for question in feedback_data:
                    if question['total'] != 0:
                        data_.append(round(question[reponse['label']] / question['total'], 2))
                        if not question['question__code'] in self.labels:
                            self.labels.append(question['question__code'])
                dataset = DataSet(label=reponse['reponse'], data=data_, color=reponse['color'])

                self.data.append(dataset)
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request, "ERREUR: echec de création du graphique des feedbacks.")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return self.data


class DeliberationListView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/filter_list.html'
    success_message = "Choisir la formation pour les délibérations. Privilégiez le format Résumé plus rapide à générer."

    def test_func(self):
        return self.request.user.is_scolarite() or self.request.user.is_direction()

    def get_queryset(self, **kwargs):
        return Formation.objects.all().order_by('-annee_univ__annee_univ', 'programme__ordre')

    def get_context_data(self, **kwargs):
        context = super(DeliberationListView, self).get_context_data(**kwargs)

        filter_ = FormationFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()

        table = DeliberationFormationTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['titre'] = 'Délibérations'
        context['filter'] = filter_
        context['table'] = table
        context['back'] = reverse('home')
        return context


def get_resultat_list_context(formation_pk):
    """
    cette fonction fabrique le context des résultats détaillés par semestre/UE/matière pour chaque inscrit
    """
    formation_ = Formation.objects.get(id=formation_pk)
    inscription_list = formation_.inscriptions_pour_deliberations().order_by('rang')

    resultat_list = {}
    for inscription_ in inscription_list:
        for periode_ in formation_.programme.periodes.all():
            ue_list = []
            for ue in periode_.ues.filter(nature='OBL'):
                ue_list.append(ue)
            inscription_periode_ = inscription_.inscription_periodes.get(periodepgm=periode_)
            for ue in inscription_periode_.groupe.option.filter(periode=periode_):
                if not ue in ue_list:
                    ue_list.append(ue)
            for ue in ue_list:
                for matiere in ue.matieres.all():
                    resultat_ = Resultat.objects.get(inscription=inscription_, module__matiere__code=matiere.code)
                    key_ = inscription_.etudiant.matricule + '_' + periode_.periode.code + '_' + str(
                        ue.id) + '_' + matiere.code
                    resultat_list[key_] = resultat_
                key_ = inscription_.etudiant.matricule + '_' + str(ue.id) + '_moy'
                resultat_list[key_] = round(resultat_.resultat_ue.moyenne(), 2)
            key_ = inscription_.etudiant.matricule + '_' + periode_.periode.code + '_moy'
            resultat_list[key_] = round(resultat_.resultat_ue.inscription_periode.moy, 2)
            key_ = inscription_.etudiant.matricule + '_' + periode_.periode.code + '_ne'
            resultat_list[key_] = resultat_.resultat_ue.inscription_periode.nb_ne()
            key_ = inscription_.etudiant.matricule + '_' + periode_.periode.code + '_rang'
            resultat_list[key_] = resultat_.resultat_ue.inscription_periode.rang

        key_ = inscription_.etudiant.matricule + '_moy'
        resultat_list[key_] = round(inscription_.moy, 2)
    return resultat_list


class PVDeleteView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, DeleteView):
    model = PV
    template_name = 'scolar/delete.html'
    success_message = "Le PV a bien été supprimé."

    def test_func(self):
        return self.request.user.is_direction()

    def get_success_url(self):
        return reverse('deliberation_list')


class PVListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    login_url = settings.LOGIN_URL
    template_name = 'scolar/filter_list.html'

    def test_func(self):
        return self.request.user.is_enseignant() or self.request.user.is_staff_only()

    def get_queryset(self, **kwargs):
        return PV.objects.filter(reserve=False).order_by('-date', '-formation__annee_univ__annee_univ',
                                                         'formation__programme__ordre', 'periode__ordre', )

    def get_context_data(self, **kwargs):
        context = super(PVListView, self).get_context_data(**kwargs)
        filter_ = PVFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()
        pv_list = PVEnseignantTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(pv_list)
        context['filter'] = filter_
        context['table'] = pv_list
        context['titre'] = 'List de procés verbaux de délibérations'
        return context


class DeliberationDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    login_url = settings.LOGIN_URL
    template_name = 'scolar/deliberation_detail.html'

    def test_func(self):
        return self.request.user.is_scolarite() or self.request.user.is_direction()

    def get_context_data(self, **kwargs):
        context = super(DeliberationDetailView, self).get_context_data(**kwargs)
        formation_ = Formation.objects.get(id=self.kwargs.get('formation_pk'))

        context['formation'] = formation_
        pv_list = PVTable(PV.objects.filter(formation=formation_), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(pv_list)
        context['pv_list'] = pv_list
        return context


@login_required
def confirmer_deliberation_view(request, formation_pk):
    if not request.user.is_direction():
        messages.error(request, "Vous n'avez pas les permissions pour accéder à cette vue.")
        return redirect('/accounts/login/?next=%s' % request.path)
    try:
        formation_ = get_object_or_404(Formation, id=formation_pk)
        # submit as background task
        t = threading.Thread(target=task_confirmer_deliberation, args=[formation_, request.user])
        t.setDaemon(True)
        t.start()
        messages.info(request,
                      "Votre demande de confirmation du PV de délibérations et envoi des décisions est prise en compte. Vous recevrez une notification aussitôt généré.")
        # redirect to a new URL:
        return HttpResponseRedirect(reverse('deliberation_detail', kwargs={'formation_pk': formation_pk, }))
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request, "ERREUR: lors de la demande de confirmation des délibérations.")
    return HttpResponseRedirect(reverse('deliberation_detail', kwargs={'formation_pk': formation_pk, }))


@transaction.atomic
def task_confirmer_deliberation(formation_, user):
    try:
        email_list = ()
        non_envoye = ''
        for inscription_ in formation_.inscriptions_pour_deliberations():
            inscription_.decision_jury = inscription_.proposition_decision_jury
            inscription_.save(update_fields=['decision_jury', ])

            # marquer les modules acquis
            Resultat.objects.filter(inscription=inscription_, moy_post_delib__gte=10).update(acquis=True)

            moyenne_rachat_str = 'Moyenne de Rachat' + str(
                inscription_.moyenne_post_delib()) + '\n' if inscription_.decision_jury in ['AR', 'CR'] else ''

            try:
                recipient_ = [inscription_.etudiant.user.email]
                email = ('[Talents] Décision du Jury de Déliberation',
                         'Bonjour ' + str(inscription_.etudiant.nom) + ' ' + str(inscription_.etudiant.prenom) + ',\n' +
                         'Le jury a délibéré\n' +
                         'Identification: ' + str(inscription_.etudiant) + '\n' +
                         'Décision du jury: ' + dict(DECISIONS_JURY)[inscription_.decision_jury] + '\n' +
                         'Moyenne Annuelle: ' + str(inscription_.moy) + '\n' +
                         moyenne_rachat_str +
                         'Rang: ' + str(inscription_.rang) + '\n' +
                         'Vous pouvez avoir accès à tous les détails concernant vos résultats dans votre compte Talents.\n' +
                         'Ceci est un message automatique. Il ne peut servir pour faire valoir vos droits. Seul le PV signé par le conseil fait foi.\n' +
                         'Bien cordialement.\n' +
                         'Département',
                         'talents@esi.dz',
                         recipient_)
                email_list += (email,)
            except Exception:
                non_envoye += str(inscription_) + '\n'
                continue
        if settings.EMAIL_ENABLED:
            send_mass_mail(email_list, fail_silently=False)

        erreur_envoi = 'Erreurs d\'envoi de notifications :\n' + non_envoye if non_envoye != '' else ''

        email = EmailMessage('[Talents] Confirmation des délibérations de la formation ' + str(formation_),
                             'Bonjour,\n' +
                             'La confirmation du PV de délibération de ' + str(
                                 formation_) + ' et envoi des décisions est terminée \n' +
                             erreur_envoi +
                             'Nous vous en remercions \n' +
                             'Bien cordialement.\n' +
                             'Département', to=[user.email])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=False)

    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage(
                '[Talents] Erreur lors de la confirmation du PV de délibération la formation ' + str(formation_),
                'Bonjour,\n' +
                'Une erreur s\'est produite lors de la confirmation des délibérations de la formation ' + str(
                    formation_) + '\n' +
                'Bien cordialement.\n' +
                'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)


# def task_confirmer_deliberation(formation_, user):
#     try:
#         non_envoye=''
#         for inscription_ in formation_.inscriptions_pour_deliberations():
#             inscription_.decision_jury=inscription_.proposition_decision_jury
#             inscription_.save(update_fields=['decision_jury',])
#
#             #marquer les modules acquis
#             Resultat.objects.filter(inscription=inscription_, moy_post_delib__gte=10).update(acquis=True)
#
#             moyenne_rachat_str = 'Moyenne de Rachat' + str(inscription_.moyenne_post_delib())+'\n' if inscription_.decision_jury in ['AR', 'CR'] else ''
#
#
#             try:
#                 email_= inscription_.etudiant.user.email
#                 email = EmailMessage('[Talents] Décision du Jury de Déliberation',
#                                      'Bonjour '+str(inscription_.etudiant.nom)+' '+str(inscription_.etudiant.prenom)+',\n'+
#                                      'Le jury a délibéré\n'+
#                                      'Identification: '+str(inscription_.etudiant)+'\n'+
#                                      'Décision du jury: '+dict(DECISIONS_JURY)[inscription_.decision_jury]+'\n'+
#                                      'Moyenne Annuelle: '+str(inscription_.moy)+'\n'+
#                                       moyenne_rachat_str +
#                                      'Rang: '+str(inscription_.rang)+'\n'+
#                                      'Vous pouvez avoir accès à tous les détails concernant vos résultats dans votre compte Talents.\n'+
#                                      'Ceci est un message automatique. Il ne peut servir pour faire valoir vos droits. Seul le PV signé par le conseil fait foi.\n'+
#                                      'Bien cordialement.\n'+
#                                      'Département', to=[email_] )
#                 if settings.EMAIL_ENABLED :
#                     email.send(fail_silently=False)
#             except Exception:
#                 non_envoye+=str(inscription_)+'\n'
#                 continue
#
#         erreur_envoi= 'Erreurs d\'envoi de notifications :\n'+ non_envoye if non_envoye != '' else ''
#
#         email = EmailMessage('[Talents] Confirmation des délibérations de la formation '+str(formation_),
#                              'Bonjour,\n'+
#                              'La confirmation du PV de délibération de '+str(formation_)+' et envoi des décisions est terminée \n'+
#                              erreur_envoi+
#                              'Nous vous en remercions \n'+
#                              'Bien cordialement.\n'+
#                              'Département', to=[user.email] )
#         if settings.EMAIL_ENABLED:
#             email.send(fail_silently=False)
#
#     except Exception:
#         if settings.DEBUG:
#             raise Exception
#         else:
#             email = EmailMessage('[Talents] Erreur lors de la confirmation du PV de délibération la formation '+str(formation_),
#                                  'Bonjour,\n'+
#                                  'Une erreur s\'est produite lors de la confirmation des délibérations de la formation '+str(formation_)+'\n'+
#                                  'Bien cordialement.\n'+
#                                  'Département', to=[user.email] )
#             if settings.EMAIL_ENABLED:
#                 email.send(fail_silently=True)

def deliberation_annuelle_settings_view(request, formation_pk):
    if not request.user.is_direction():
        messages.error(request, "Vous n'avez pas les permissions pour accéder à cette vue.")
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    formation_ = Formation.objects.get(id=formation_pk)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SelectPVAnnuelSettingsForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # submit as background task
            t = threading.Thread(target=task_deliberation_annuelle, args=[form, formation_, request.user])
            t.setDaemon(True)
            t.start()
            messages.info(request,
                          "Votre demande de génération du PV est prise en compte. Vous recevrez une notification aussitôt généré.")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('deliberation_detail', kwargs={'formation_pk': formation_pk, }))
    # if a GET (or any other method) we'll create a blank form
    else:
        form = SelectPVAnnuelSettingsForm()
        messages.info(request, "Indiquez la configuration du PV de délibération annuelle à générer.")
    return render(request, 'scolar/deliberation_annuelle_settings.html', {'form': form, 'formation': formation_})


# @transaction.atomic
# def task_deliberation_annuelle(form_, formation_, user):
#     context={}
#     data=form_.cleaned_data
#     try:
#         sort_=data['sort'] # indique comment trier les étudiants par rang (pour délibérer) ou par groupe (pour vérifier les notes)
#
#         periode_list ={}
#         for periode_ in formation_.programme.periodes.all():
#             periode_list[periode_.id]={}
#             periode_list[periode_.id]['periode']=periode_
#             periode_list[periode_.id]['ues']=[]
#             for ue in periode_.ues.filter(nature='OBL'):
#                 if not ue in periode_list[periode_.id]['ues']:
#                     periode_list[periode_.id]['ues'].append(ue)
#             for groupe_ in Groupe.objects.filter(section__formation=formation_):
#                 for ue in groupe_.option.filter(periode=periode_):
#                     if not ue in  periode_list[periode_.id]['ues']:
#                         periode_list[periode_.id]['ues'].append(ue)
#         if sort_:
#             inscription_list=formation_.inscriptions_pour_deliberations().order_by('rang')
#         else:
#             inscription_list=formation_.inscriptions_pour_deliberations().order_by('groupe__code', 'etudiant__nom', 'etudiant__prenom')
#
#         context['resultat_list']=get_resultat_list_context(formation_.id)
#         context['formation'] = formation_
#         context['inscription_list']=inscription_list
#         context['decisions_jury']=dict(DECISIONS_JURY)
#         context['signatures']=data['signatures']
#         context['date'] = datetime.date.today()
#         context['photo'] = data['photo']
#         context['anonyme'] = data['anonyme']
#         context['ne'] = data['ne']
#         context['moy_ue'] = data['moy_ue']
#         context['rang'] = data['rang']
#         context['rachat'] = data['rachat']
#         context['periode_list'] = periode_list
#         context['institution'] = user.institution()
#
#         pv, created=PV.objects.update_or_create(formation=formation_, annuel=True, tri_rang=data['sort'], anonyme=data['anonyme'],
#                                     photo=data['photo'], note_eliminatoire=data['ne'], moy_ue=data['moy_ue'],
#                                     reserve=data['reserve'], rang=data['rang'], signature=data['signatures'], defaults={
#                                         'formation':formation_,
#                                         'annuel':True,
#                                         'tri_rang':data['sort'],
#                                         'anonyme':data['anonyme'],
#                                         'photo':data['photo'],
#                                         'note_eliminatoire':data['ne'],
#                                         'moy_ue':data['moy_ue'],
#                                         'rang':data['rang'],
#                                         'reserve':data['reserve'],
#                                         'signature':data['signatures'],
#                                         'content': render_to_string('scolar/deliberation_annuelle.html', context)
#                                         })
#     except Exception:
#         if settings.DEBUG:
#             raise Exception
#         else:
#             email = EmailMessage('[Talents] Erreur lors de la génération du PV de  la formation '+str(formation_),
#                                  'Bonjour,\n'+
#                                  'Une erreur s\'est produite lors de la génération de la formation '+str(formation_)+'\n'+
#                                  'Veuillez vérifier les notes et réessayer \n'+
#                                  'Bien cordialement.\n'+
#                                  'Département', to=[user.email] )
#             if settings.EMAIL_ENABLED:
#                 email.send(fail_silently=True)
#     else:
#         print('[Talents] Confirmation de la génération du PV de la formation '+str(formation_))
#         email = EmailMessage('[Talents] Confirmation de la génération du PV de la formation '+str(formation_),
#                              'Bonjour,\n'+
#                              'La génération du PV de délibération de '+str(formation_)+' est terminée \n'+
#                              'Nous vous en remercions \n'+
#                              'Bien cordialement.\n'+
#                              'Département', to=[user.email] )
#         if settings.EMAIL_ENABLED:
#             email.send(fail_silently=True)


@transaction.atomic
def task_deliberation_annuelle(form_, formation_, user):
    context = {}
    data = form_.cleaned_data
    try:
        sort_ = data[
            'sort']  # indique comment trier les étudiants par rang (pour délibérer) ou par groupe (pour vérifier les notes)

        header = ['Matricule', 'Nom', 'Prenom']
        periode_list = {}
        for periode_ in formation_.programme.periodes.all():
            header.append("Groupe_" + periode_.periode.code)
            periode_list[periode_.id] = {}
            periode_list[periode_.id]['periode'] = periode_
            periode_list[periode_.id]['ues'] = []
            for ue in periode_.ues.filter(nature='OBL'):
                if not ue in periode_list[periode_.id]['ues']:
                    periode_list[periode_.id]['ues'].append(ue)
                    for matiere_ in ue.matieres.all():
                        header.append(matiere_.code)
                    header.append(ue.code)

            for groupe_ in Groupe.objects.filter(section__formation=formation_):
                for ue in groupe_.option.filter(periode=periode_):
                    if not ue in periode_list[periode_.id]['ues']:
                        periode_list[periode_.id]['ues'].append(ue)
                        for matiere_ in ue.matieres.all():
                            header.append(matiere_.code)
                        header.append(ue.code)
            header.append("Ne_" + periode_.periode.code)
            header.append("Rang_" + periode_.periode.code)
            header.append("Moy_" + periode_.periode.code)
        header.append("Rang_annuel")
        header.append("Moy_annuelle")
        header.append("Moy_rachat")
        header.append("Decision_jury")

        if sort_:
            inscription_list = formation_.inscriptions_pour_deliberations().order_by('rang')
        else:
            inscription_list = formation_.inscriptions_pour_deliberations().order_by('groupe__code', 'etudiant__nom',
                                                                                     'etudiant__prenom')

        context['resultat_list'] = get_resultat_list_context(formation_.id)
        context['formation'] = formation_
        context['inscription_list'] = inscription_list
        context['decisions_jury'] = dict(DECISIONS_JURY)
        context['signatures'] = data['signatures']
        context['date'] = datetime.date.today()
        context['photo'] = data['photo']
        context['anonyme'] = data['anonyme']
        context['ne'] = data['ne']
        context['moy_ue'] = data['moy_ue']
        context['rang'] = data['rang']
        context['rachat'] = data['rachat']
        context['periode_list'] = periode_list
        context['institution'] = user.institution()

        pv, created = PV.objects.update_or_create(formation=formation_, date=datetime.date.today(), annuel=True,
                                                  tri_rang=data['sort'], anonyme=data['anonyme'],
                                                  photo=data['photo'], note_eliminatoire=data['ne'],
                                                  moy_ue=data['moy_ue'],
                                                  reserve=data['reserve'], rang=data['rang'],
                                                  signature=data['signatures'], defaults={
                'date': datetime.date.today(),
                'formation': formation_,
                'annuel': True,
                'tri_rang': data['sort'],
                'anonyme': data['anonyme'],
                'photo': data['photo'],
                'note_eliminatoire': data['ne'],
                'moy_ue': data['moy_ue'],
                'rang': data['rang'],
                'reserve': data['reserve'],
                'signature': data['signatures'],
                'content': render_to_string('scolar/deliberation_annuelle.html', context)
            })
        if data['xls']:
            inscription_list = formation_.inscriptions_pour_deliberations().order_by('rang')

            sheet = Dataset()
            sheet.headers = header

            for inscrit_ in inscription_list:
                row_ = []
                row_.append(inscrit_.etudiant.matricule)
                row_.append(inscrit_.etudiant.nom)
                row_.append(inscrit_.etudiant.prenom)

                for key_, periode_ in periode_list.items():
                    inscription_periode_ = inscrit_.inscription_periodes.get(periodepgm=periode_['periode'])
                    row_.append(inscription_periode_.groupe.code)
                    for ue_ in periode_['ues']:
                        resultat_ = None
                        for matiere_ in ue_.matieres.all():
                            try:
                                resultat_ = Resultat.objects.get(inscription=inscrit_, resultat_ue__ue=ue_,
                                                                 module__matiere__code=matiere_.code)
                                row_.append(resultat_.moy_post_delib)
                            except Exception:
                                row_.append('')
                        if resultat_:
                            row_.append(resultat_.resultat_ue.moyenne_post_delib())
                        else:
                            row_.append('')
                    row_.append(inscription_periode_.nb_ne())
                    row_.append(inscription_periode_.rang)
                    row_.append(inscription_periode_.moy)
                row_.append(inscrit_.rang)
                row_.append(inscrit_.moy)
                row_.append(inscrit_.moyenne_post_delib())
                if inscrit_.proposition_decision_jury.startswith('M'):
                    row_.append("Maladie")
                else:
                    row_.append(dict(DECISIONS_JURY)[inscrit_.proposition_decision_jury])

                sheet.append(row_)

            filename = "PV_" + str(formation_) + '.xlsx'
            filename = filename.replace(' ', '_')
            email = EmailMessage('[Talents] Génération du PV de ' + str(formation_),
                                 'Bonjour,\n' +
                                 'La génération du PV de délibération de ' + str(formation_) + ' est terminée \n' +
                                 'Veuillez trouver ci-joint le PV au format Excel\n' +
                                 'Bien cordialement.\n' +
                                 'Département',
                                 to=[user.email, formation_.programme.departement.responsable.user.email] +
                                    settings.STAFF_EMAILS['scolarite'] +
                                    settings.STAFF_EMAILS['direction'])
            email.attach(filename, sheet.xlsx, 'application/vnd.ms-excel')
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)

    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage('[Talents] Erreur lors de la génération du PV de  la formation ' + str(formation_),
                                 'Bonjour,\n' +
                                 'Une erreur s\'est produite lors de la génération de la formation ' + str(
                                     formation_) + '\n' +
                                 'Veuillez vérifier les notes et réessayer \n' +
                                 'Bien cordialement.\n' +
                                 'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)
    else:
        if not data['xls']:
            email = EmailMessage('[Talents] Confirmation de la Génération du PV de ' + str(formation_),
                                 'Bonjour,\n' +
                                 'La génération du PV de délibération de ' + str(formation_) + ' est terminée \n' +
                                 'Bien cordialement.\n' +
                                 'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)


@login_required
def export_pv_view(request, formation_pk):
    if not (request.user.is_scolarite() or request.user.is_direction()):
        messages.error(request, "Vous n'êtes pas autorisé à excéuter cette opération.")
        return redirect('/accounts/login/?next=%s' % request.path)

    try:
        # Create the HttpResponse object with the appropriate CSV header.
        formation_ = get_object_or_404(Formation, id=formation_pk)
        header = ['Matricule', 'Nom', 'Prenom']
        periode_list = {}
        for periode_ in formation_.programme.periodes.all():
            header.append("Groupe_" + periode_.periode.code)
            periode_list[periode_.id] = {}
            periode_list[periode_.id]['periode'] = periode_
            periode_list[periode_.id]['ues'] = []
            for ue in periode_.ues.filter(nature='OBL'):
                if not ue in periode_list[periode_.id]['ues']:
                    periode_list[periode_.id]['ues'].append(ue)
                    for matiere_ in ue.matieres.all():
                        header.append(matiere_.code)
                    header.append(ue.code)

            for groupe_ in Groupe.objects.filter(section__formation=formation_):
                for ue in groupe_.option.filter(periode=periode_):
                    if not ue in periode_list[periode_.id]['ues']:
                        periode_list[periode_.id]['ues'].append(ue)
                        for matiere_ in ue.matieres.all():
                            header.append(matiere_.code)
                        header.append(ue.code)
            header.append("Ne_" + periode_.periode.code)
            header.append("Rang_" + periode_.periode.code)
            header.append("Moy_" + periode_.periode.code)
        header.append("Rang_annuel")
        header.append("Moy_annuelle")
        header.append("Moy_rachat")
        header.append("Decision_jury")

        inscription_list = formation_.inscriptions_pour_deliberations().order_by('rang')

        sheet = Dataset()
        sheet.headers = header

        for inscrit_ in inscription_list:
            row_ = []
            row_.append(inscrit_.etudiant.matricule)
            row_.append(inscrit_.etudiant.nom)
            row_.append(inscrit_.etudiant.prenom)

            for key_, periode_ in periode_list.items():
                inscription_periode_ = inscrit_.inscription_periodes.get(periodepgm=periode_['periode'])
                row_.append(inscription_periode_.groupe.code)
                for ue_ in periode_['ues']:
                    resultat_ = None
                    for matiere_ in ue_.matieres.all():
                        try:
                            resultat_ = Resultat.objects.get(inscription=inscrit_, module__matiere__code=matiere_.code)
                            row_.append(resultat_.moy_post_delib)
                        except Exception:
                            row_.append('')
                    if resultat_:
                        row_.append(resultat_.resultat_ue.moyenne_post_delib())
                    else:
                        row_.append('')
                row_.append(inscription_periode_.ne)
                row_.append(inscription_periode_.rang)
                row_.append(inscription_periode_.moy)
            row_.append(inscrit_.rang)
            row_.append(inscrit_.moy)
            row_.append(inscrit_.moyenne_post_delib())
            row_.append(dict(DECISIONS_JURY)[inscrit_.decision_jury])

            sheet.append(row_)

        filename = str(formation_) + '.xlsx'
        filename = filename.replace(' ', '_')

        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=' + filename + ";"
        response.write(sheet.xlsx)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: Il y a eu une erreur lors de l'export du PV. Merci de le signaler à l'administrateur.")
    return response


# def get_resultat_list_provisoire_context(formation_pk, matieres_moyenne, periode_cible):
#     """
#     cette fonction fabrique le context des résultats détaillés par semestre/UE/matière pour chaque inscrit
#     """
#     formation_=Formation.objects.get(id = formation_pk)
#     inscription_list=formation_.inscriptions_pour_deliberations()
#
#     resultat_list={}
#     for inscription_ in inscription_list:
#         for periode_ in formation_.programme.periodes.all() :
#             moy=0
#             sum_coef=0
#             ue_list=[]
#             for ue in periode_.ues.filter(nature='OBL') :
#                 ue_list.append(ue)
#             inscription_periode_=inscription_.inscription_periodes.get(periodepgm=periode_)
#             for ue in inscription_periode_.groupe.option.filter(periode=periode_):
#                 if not ue in ue_list:
#                     ue_list.append(ue)
#             for ue in ue_list:
#                 for matiere in ue.matieres.all() :
#                     resultat_=Resultat.objects.get(inscription=inscription_, module__matiere__code=matiere.code)
#                     key_=inscription_.etudiant.matricule+'_'+periode_.periode.code+'_'+matiere.code
#                     resultat_list[key_]=resultat_
#                     if resultat_.module.matiere.code in matieres_moyenne:
#                         moy+=resultat_.moy*resultat_.module.matiere.coef
#                         sum_coef+=resultat_.module.matiere.coef
#             key_=inscription_.etudiant.matricule+'_'+periode_.periode.code+'_moy'
#             moy_=round(moy/sum_coef,2) if sum_coef!=0 else 0
#             resultat_list[key_]=moy_
#
#
#             key_=inscription_.etudiant.matricule+'_'+periode_.periode.code+'_ne'
#             ne_=resultat_.resultat_ue.inscription_periode.nb_ne_parmis_matieres(matieres_moyenne)
#             resultat_list[key_]=ne_
#
#             if inscription_periode_.periode==periode_cible:
#                 inscription_periode_.moy=moy_
#                 inscription_periode_.ne=ne_
#                 inscription_periode_.save(update_fields=['moy','ne'])
#
#     for inscription_ in inscription_list:
#         inscription_periode_=inscription_.inscription_periodes.get(periodepgm__periode=periode_cible)
#         key_=inscription_.etudiant.matricule+'_'+inscription_periode_.periodepgm.code+'_rang'
#         rang_=inscription_periode_.ranking()
#         resultat_list[key_]=rang_
#         inscription_periode_.rang=rang_
#         inscription_periode_.save(update_fields=['rang'])
#
#         #key_=inscription_.etudiant.matricule+'_moy'
#         #resultat_list[key_]=round(inscription_.moy,2)
#     return resultat_list

def get_resultat_list_provisoire_context(formation_pk, matieres_moyenne):
    """
    cette fonction fabrique le context des résultats détaillés par semestre/UE/matière pour chaque inscrit
    """
    formation_ = Formation.objects.get(id=formation_pk)
    inscription_list = formation_.inscriptions_pour_deliberations()

    resultat_list = {}
    for inscription_ in inscription_list:
        for periode_ in formation_.programme.periodes.all():
            moy = 0
            sum_coef = 0
            ue_list = []
            for ue in periode_.ues.filter(nature='OBL'):
                ue_list.append(ue)
            inscription_periode_ = inscription_.inscription_periodes.get(periodepgm=periode_)
            for ue in inscription_periode_.groupe.option.filter(periode=periode_):
                if not ue in ue_list:
                    ue_list.append(ue)
            for ue in ue_list:
                for matiere in ue.matieres.all():
                    resultat_ = Resultat.objects.get(inscription=inscription_, module__matiere__code=matiere.code)
                    key_ = inscription_.etudiant.matricule + '_' + periode_.periode.code + '_' + matiere.code
                    resultat_list[key_] = resultat_
                    if resultat_.module.matiere.code in matieres_moyenne:
                        moy += resultat_.moy * resultat_.module.matiere.coef
                        sum_coef += resultat_.module.matiere.coef
            key_ = inscription_.etudiant.matricule + '_' + periode_.periode.code + '_moy'
            resultat_list[key_] = round(moy / sum_coef, 2) if sum_coef != 0 else 0
            key_ = inscription_.etudiant.matricule + '_' + periode_.periode.code + '_ne'
            resultat_list[key_] = resultat_.resultat_ue.inscription_periode.nb_ne_parmis_matieres(matieres_moyenne)
            key_ = inscription_.etudiant.matricule + '_' + periode_.periode.code + '_rang'
            resultat_list[key_] = resultat_.resultat_ue.inscription_periode.ranking()

        key_ = inscription_.etudiant.matricule + '_moy'
        resultat_list[key_] = round(inscription_.moy, 2)
    return resultat_list


def deliberation_provisoire_settings_view(request, formation_pk, periode_pk):
    if not request.user.is_direction():
        messages.error(request, "Vous n'avez pas les permissions pour accéder à cette vue.")
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    formation_ = Formation.objects.get(id=formation_pk)
    periode_ = Periode.objects.get(id=periode_pk)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SelectPVSettingsForm(formation_pk, request.POST)
        # check whether it's valid:
        if form.is_valid():
            # submit as background task
            t = threading.Thread(target=task_deliberation_provisoire, args=[form, formation_, periode_, request.user])
            t.setDaemon(True)
            t.start()
            messages.info(request,
                          "Votre demande de génération du PV est prise en compte. Vous recevrez une notification aussitôt généré.")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('deliberation_detail', kwargs={'formation_pk': formation_pk, }))
            # return HttpResponseRedirect("%s?%s" % (reverse('deliberation_provisoire', kwargs={'formation_pk':formation_pk, 'periode_pk':periode_pk}),
            #                                        urllib.parse.urlencode(form.cleaned_data)))
    # if a GET (or any other method) we'll create a blank form
    else:
        form = SelectPVSettingsForm(formation_pk)
        messages.info(request, "Indiquez la configuration du PV de délibération semestrielle à générer.")
    return render(request, 'scolar/deliberation_provisoire_settings.html',
                  {'form': form, 'formation': formation_, 'periode': periode_})


# @transaction.atomic
# def task_deliberation_provisoire(form_, formation_, periode, user):
#     context={}
#     data=form_.cleaned_data
#     try:
#         periode_list={}
#         for periode_ in formation_.programme.periodes.all():
#             periode_list[periode_.id]={}
#             periode_list[periode_.id]['periode']=periode_
#             periode_list[periode_.id]['matieres']=[]
#             for ue in periode_.ues.filter(nature='OBL'):
#                 for matiere in ue.matieres.all():
#                     if not matiere in periode_list[periode_.id]['matieres'] :
#                         periode_list[periode_.id]['matieres'].append(matiere)
#             for groupe_ in Groupe.objects.filter(section__formation=formation_):
#                 for ue in groupe_.option.filter(periode=periode_):
#                     for matiere in ue.matieres.all():
#                         if not matiere in periode_list[periode_.id]['matieres'] :
#                             periode_list[periode_.id]['matieres'].append(matiere)
#         resultat_list=[]
#
#         matieres_moyenne=[]
#         for periode_ in formation_.programme.periodes.all():
#             matieres_moyenne+=data['matieres_moyenne_'+periode_.periode.code]
#         #matieres_moyenne = re.split('[ ,\'\[\]]{1}', matieres_moyenne)
#         resultat_list=get_resultat_list_provisoire_context(formation_.id, matieres_moyenne, periode)
#         context['resultat_list']=resultat_list
#
#         if data['sort']==True :
#             inscription_id_list=InscriptionPeriode.objects.filter(
#                 inscription__in=formation_.inscriptions_pour_deliberations().values_list('id'),
#                 periodepgm__periode=periode
#                 ).order_by('rang').values_list('inscription')
#         else:
#             inscription_id_list=InscriptionPeriode.objects.filter(
#                 inscription__in=formation_.inscriptions_pour_deliberations().values_list('id'),
#                 periodepgm__periode=periode
#                 ).order_by('inscription__groupe__code', 'inscription__etudiant__nom', 'inscription__etudiant__prenom' ).values_list('inscription')
#         context['inscription_list']=Inscription.objects.filter(id__in=inscription_id_list)
#         context['formation'] = formation_
#         context['date'] = datetime.date.today()
#         context['photo'] = 1 if data['photo']==True else 0
#         context['anonyme'] = 1 if data['anonyme']==True else 0
#         context['ne'] = 1 if data['ne']==True else 0
#         context['rang'] = 1 if data['rang']==True else 0
#         context['signatures'] = 1 if data['signatures']==True else 0
#         context['periode_code'] = periode.code
#         context['periode_list'] = periode_list
#         context['matieres_affichage']={}
#         for periode_ in formation_.programme.periodes.all():
#             context['matieres_affichage'][periode_.periode.code] = data['matieres_affichage_'+periode_.periode.code]
#         context['matieres_moyenne'] = matieres_moyenne
#         context['institution'] = user.institution()
#
#         pv, created=PV.objects.update_or_create(formation=formation_, annuel=False, periode=periode, tri_rang=data['sort'], anonyme=data['anonyme'],
#                                     photo=data['photo'], note_eliminatoire=data['ne'], rang=data['rang'], signature=data['signatures'], defaults={
#                                         'formation':formation_,
#                                         'annuel':False,
#                                         'periode':periode,
#                                         'tri_rang':data['sort'],
#                                         'anonyme':data['anonyme'],
#                                         'photo':data['photo'],
#                                         'note_eliminatoire':data['ne'],
#                                         'rang':data['rang'],
#                                         'signature':data['signatures'],
#                                         'content': render_to_string('scolar/deliberation_provisoire_pdf.html', context)
#                                         })
#     except Exception:
#         if settings.DEBUG:
#             raise Exception
#         else:
#             email = EmailMessage('[Talents] Erreur lors de la génération du PV de  la formation '+str(formation_),
#                                  'Bonjour,\n'+
#                                  'Une erreur s\'est produite lors de la génération de la formation '+str(formation_)+'\n'+
#                                  'Veuillez vérifier les notes et réessayer \n'+
#                                  'Bien cordialement.\n'+
#                                  'Département', to=[user.email] )
#             if settings.EMAIL_ENABLED:
#                 email.send(fail_silently=True)
#     else:
#         print('[Talents] Confirmation de la génération du PV de la formation ')
#         email = EmailMessage('[Talents] Confirmation de la génération du PV de la formation '+str(formation_),
#                              'Bonjour,\n'+
#                              'La génération du PV de délibération de '+str(formation_)+' est terminée \n'+
#                              'Nous vous en remercions \n'+
#                              'Bien cordialement.\n'+
#                              'Département', to=[user.email] )
#         if settings.EMAIL_ENABLED:
#             email.send(fail_silently=True)

@transaction.atomic
def task_deliberation_provisoire(form_, formation_, periode, user):
    context = {}
    data = form_.cleaned_data
    try:
        periode_list = {}
        for periode_ in formation_.programme.periodes.all():
            periode_list[periode_.id] = {}
            periode_list[periode_.id]['periode'] = periode_
            periode_list[periode_.id]['matieres'] = []
            for ue in periode_.ues.filter(nature='OBL'):
                for matiere in ue.matieres.all():
                    if not matiere in periode_list[periode_.id]['matieres']:
                        periode_list[periode_.id]['matieres'].append(matiere)
            for groupe_ in Groupe.objects.filter(section__formation=formation_):
                for ue in groupe_.option.filter(periode=periode_):
                    for matiere in ue.matieres.all():
                        if not matiere in periode_list[periode_.id]['matieres']:
                            periode_list[periode_.id]['matieres'].append(matiere)
        resultat_list = []

        matieres_moyenne = []
        for periode_ in formation_.programme.periodes.all():
            matieres_moyenne += data['matieres_moyenne_' + periode_.periode.code]
        # matieres_moyenne = re.split('[ ,\'\[\]]{1}', matieres_moyenne)
        resultat_list = get_resultat_list_provisoire_context(formation_.id, matieres_moyenne)
        context['resultat_list'] = resultat_list

        # inscription_list=Inscription.objects.filter(formation=formation_).exclude(Q(inscription_periodes__groupe__isnull=True)|Q(decision_jury='X'))
        inscription_list = formation_.inscriptions_pour_deliberations()
        inscrits_list = []
        for inscrit in inscription_list:
            # annoter chaque inscrit de sa moyenne
            item = {}
            item['id'] = inscrit.id
            item['moy'] = resultat_list[inscrit.etudiant.matricule + '_' + periode.code + '_moy']
            inscrits_list.append(item)
        # trier les inscrits selon la moyenne portant sur les matières choisies
        inscrits_list.sort(key=operator.itemgetter('moy'), reverse=True)
        # calculer la rang de chaque inscrit et l'annoter avec
        # extraire la liste des moyennes
        moyenne_list = []
        for inscrit in inscrits_list:
            moyenne_list.append(inscrit['moy'])
        # reconstruire la liste des inscrits triée
        # calculer le rang au même temps
        sorted_inscription_list = []
        rang_list = {}
        for inscrit in inscrits_list:
            rang_list[inscrit['moy']] = moyenne_list.index(inscrit['moy']) + 1
            sorted_inscription_list.append(inscription_list.get(id=inscrit['id']))
        context['rang_list'] = rang_list
        if data['sort'] == True:
            context['inscription_list'] = sorted_inscription_list
        else:
            context['inscription_list'] = formation_.inscriptions_pour_deliberations().order_by('groupe__code',
                                                                                                'etudiant__nom',
                                                                                                'etudiant__prenom')
        context['formation'] = formation_
        context['date'] = datetime.date.today()
        context['photo'] = 1 if data['photo'] == True else 0
        context['anonyme'] = 1 if data['anonyme'] == True else 0
        context['ne'] = 1 if data['ne'] == True else 0
        context['rang'] = 1 if data['rang'] == True else 0
        context['signatures'] = 1 if data['signatures'] == True else 0
        context['periode_code'] = periode.code
        context['periode_list'] = periode_list
        context['matieres_affichage'] = {}
        for periode_ in formation_.programme.periodes.all():
            context['matieres_affichage'][periode_.periode.code] = data['matieres_affichage_' + periode_.periode.code]
        context['matieres_moyenne'] = matieres_moyenne
        context['institution'] = user.institution()

        pv, created = PV.objects.update_or_create(formation=formation_, date=datetime.date.today(), annuel=False,
                                                  periode=periode, tri_rang=data['sort'], anonyme=data['anonyme'],
                                                  photo=data['photo'], note_eliminatoire=data['ne'], rang=data['rang'],
                                                  signature=data['signatures'], defaults={
                'date': datetime.date.today(),
                'formation': formation_,
                'annuel': False,
                'periode': periode,
                'tri_rang': data['sort'],
                'anonyme': data['anonyme'],
                'photo': data['photo'],
                'note_eliminatoire': data['ne'],
                'rang': data['rang'],
                'signature': data['signatures'],
                'content': render_to_string('scolar/deliberation_provisoire_pdf.html', context)
            })
    except Exception as e:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage('[Talents] Erreur lors de la génération du PV de  la formation ' + str(formation_),
                                 'Bonjour,\n' +
                                 'Une erreur s\'est produite lors de la génération de la formation ' + str(
                                     formation_) + '\n' +
                                 'Veuillez vérifier les notes et réessayer \n' +
                                 'Bien cordialement.\n' +
                                 'Département' +
                                 str(e), to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)
    else:
        print('[Talents] Confirmation de la génération du PV de la formation ')
        email = EmailMessage('[Talents] Confirmation de la génération du PV de la formation ' + str(formation_),
                             'Bonjour,\n' +
                             'La génération du PV de délibération de ' + str(formation_) + ' est terminée \n' +
                             'Nous vous en remercions \n' +
                             'Bien cordialement.\n' +
                             'Département', to=[user.email])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)


class PVDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    template_name = 'scolar/pv_detail.html'
    model = PV

    def test_func(self):
        return self.request.user.is_enseignant() or self.request.user.is_staff_only()


@login_required
def deliberation_calcul_view(request, formation_pk):
    if not (request.user.is_direction()):
        return redirect('/accounts/login/?next=%s' % request.path)

    try:
        formation_ = get_object_or_404(Formation, id=formation_pk)
        # submit as background task
        t = threading.Thread(target=task_deliberation_calcul, args=[formation_, request.user])
        t.setDaemon(True)
        t.start()
        messages.success(request,
                         "Votre demande de calcul des moyennes et rangs est prise en compte. Une notification vous sera transmise aussitôt terminée.")
        # redirect to a new URL:
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: une erreur s'est produite lors de la demande de calcul des moyennes et rangs. Merci de le signaler à l'administrateur.")
    return HttpResponseRedirect(reverse('deliberation_detail', kwargs={'formation_pk': formation_pk, }))


@transaction.atomic
def task_deliberation_calcul(formation_, user):
    try:
        for inscription_ in formation_.inscriptions_pour_deliberations():
            # màj moyenne et rang de chaque semestre
            for periode_ in inscription_.inscription_periodes.all():
                periode_.moy = periode_.moyenne()
                # periode_.moy_post_delib = periode_.moyenne_post_delib()
                periode_.ne = periode_.nb_ne()
                # periode_.save(update_fields=['ne', 'moy', 'moy_post_delib'])
                periode_.save(update_fields=['ne', 'moy'])
                for ue_ in periode_.resultat_ues.all():
                    ue_.moy = ue_.moyenne()
                    ue_.save(update_fields=['moy'])
        for inscription_ in formation_.inscriptions_pour_deliberations():
            for periode_ in inscription_.inscription_periodes.all():
                periode_.rang = periode_.ranking()
                periode_.save(update_fields=['rang'])

                # màj ECTS pour chaque résultat et indiquer modules acquis
                for ue_ in periode_.resultat_ues.all():
                    for resultat_ in ue_.resultat_matieres.all():
                        resultat_.ects = resultat_.calcul_ects()
                        # resultat_.ects_post_delib=resultat_.ects
                        resultat_.save(update_fields=['ects'])

            inscription_.moy = inscription_.moyenne()
            # inscription_.moy_post_delib=inscription_.moyenne_post_delib()
            # faire une proposition automatique de la décision selon la moyenne et décision actuelle (abandon, maladie ou encours
            if inscription_.proposition_decision_jury == 'X':
                if inscription_.moy >= 10 and inscription_.nb_ne() == 0:
                    if formation_.programme.concours:
                        inscription_.proposition_decision_jury = 'AC'
                    else:
                        inscription_.proposition_decision_jury = 'A'
                else:
                    inscription_.proposition_decision_jury = inscription_.decision_jury

            inscription_.save(update_fields=['moy', 'proposition_decision_jury'])
        for inscription_ in formation_.inscriptions_pour_deliberations():
            inscription_.rang = inscription_.ranking()
            inscription_.save(update_fields=['rang'])
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage(
                '[Talents] Erreur lors de la génération du PV de délibération de la formation ' + str(formation_),
                'Bonjour,\n' +
                'Une erreur s\'est produite lors de la génération du PV de délibération de la formation ' + str(
                    formation_) + '\n' +
                'Bien cordialement.\n' +
                'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)
    else:
        email = EmailMessage(
            '[Talents] Confirmation de calcul du PV de délibération de la formation ' + str(formation_),
            'Bonjour,\n' +
            'Le calcul du PV de délibération de ' + str(formation_) + ' est terminée \n' +
            'Nous vous en remercions \n' +
            'Bien cordialement.\n' +
            'Département', to=[user.email])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)


def note_eliminatoire_update_view(request, formation_pk):
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    formation_ = Formation.objects.get(id=formation_pk)
    module_list = Module.objects.filter(formation=formation_)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SelectModuleForm(formation_pk, request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                data = form.cleaned_data

                for periode_ in formation_.programme.periodes.all():
                    module_list_ = Module.objects.filter(formation=formation_, periode=periode_)
                    for module_ in module_list_:
                        if data['select_module_' + str(module_.id)]:
                            module_.note_eliminatoire = data['calcul_ne_' + str(module_.id)]
                            module_.save(update_fields=['note_eliminatoire'])
            except Exception:
                if settings.DEBUG:
                    raise Exception("Erreur lors de la mise à jour des notes élimibatoire")
                else:
                    messages.error(request,
                                   "ERREUR: les notes éliminatoires n'ont pu être mises à jours à cause d'erreurs lors du calcul.")
                    return HttpResponseRedirect(reverse('deliberation_detail', kwargs={'formation_pk': formation_pk, }))
            # redirect to a new URL:
            messages.success(request, "Les notes élimibatoires ont été enregistrées avec succès!")
            messages.info(request, "Vous pouvez lancer le calcul du PV de délibérations.")
            return render(request, 'scolar/note_eliminatoire_update.html',
                          {'form': form, 'module_list': module_list, 'formation': formation_})
            # if a GET (or any other method) we'll create a blank form
    else:
        form = SelectModuleForm(formation_pk)
        messages.info(request, "Cochez les modules pour lesquels vous voulez enregistrer la note éliminatoire")
    return render(request, 'scolar/note_eliminatoire_update.html',
                  {'form': form, 'module_list': module_list, 'formation': formation_})


class NotesEliminatoiresPVPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/notes_eliminatoires_pv_pdf.html'
    cmd_options = {
        'orientation': 'Landscape',
        'page-size': 'A4',
    }

    def test_func(self):
        return self.request.user.is_scolarite() or self.request.user.is_direction()

    def get_context_data(self, **kwargs):
        context = super(NotesEliminatoiresPVPDFView, self).get_context_data(**kwargs)
        formation_ = Formation.objects.get(id=self.kwargs.get('formation_pk'))
        periode_ = PeriodeProgramme.objects.get(id=self.kwargs.get('periode_pk'))
        self.filename = 'PV_NOTES_ELIMINATOIRES_' + str(formation_) + '_' + periode_.periode.code + '.pdf'
        ue_list = []
        for ue in periode_.ues.filter(nature='OBL'):
            ue_list.append(ue)
        for groupe_ in Groupe.objects.filter(section__formation=formation_):
            for ue in groupe_.option.filter(periode=periode_):
                ue_list.append(ue)
        module_list = {}
        for module_ in Module.objects.filter(formation=formation_, periode=periode_):
            if not module_.matiere.code in module_list.keys():
                module_list[module_.matiere.code] = module_
        context['formation'] = formation_
        context['periode'] = periode_
        context['ue_list'] = ue_list
        context['module_list'] = module_list
        context['date'] = datetime.date.today()
        return context


class NotesEliminatoiresPVProvisoirePDFView(NotesEliminatoiresPVPDFView):
    template_name = 'scolar/notes_eliminatoires_pv_provisoire_pdf.html'


class FeedbackModuleView(LoginRequiredMixin, TemplateView):
    template_name = 'scolar/feedback_module.html'

    def test_func(self):
        if self.request.user.is_direction():
            return True
        elif self.request.user.is_enseignant():
            module_ = get_object_or_404(Module, id=self.kwargs.get('module_pk'))
            return assure_module(self.request.user.enseignant, module_)
        else:
            return False

    def get_context_data(self, **kwargs):
        context = super(FeedbackModuleView, self).get_context_data(**kwargs)
        module_pk_ = self.kwargs.get('module_pk')
        module_ = get_object_or_404(Module, id=module_pk_)
        feedback_list = Feedback.objects.filter(module=module_, show=True)
        feedback_chart_ = FeedbackChart(module_pk=module_pk_)
        question_list = Question.objects.all().order_by('code')
        context['feedback_chart'] = feedback_chart_
        context['module'] = module_
        if self.test_func():
            context['feedback_list'] = feedback_list
        context['question_list'] = question_list
        try:
            context['nb_reponses'] = Reponse.objects.filter(feedback__module=module_).exclude(reponse='').distinct(
                'feedback').count()
        except Exception:
            context['nb_reponses'] = Feedback.objects.filter(module=module_).count()
        context['nb_inscrits'] = module_.formation.inscriptions_actives().count()

        return context


class FeedbackModulePDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/feedback_module_pdf.html'

    # cmd_options=settings.WKHTMLTOPDF_CMD_OPTIONS

    def test_func(self):
        if self.request.user.is_direction():
            return True
        elif self.request.user.is_enseignant():
            module_ = get_object_or_404(Module, id=self.kwargs.get('module_pk'))
            return assure_module(self.request.user.enseignant, module_)
        else:
            return False

    def get_context_data(self, **kwargs):
        context = super(FeedbackModulePDFView, self).get_context_data(**kwargs)
        module_pk_ = self.kwargs.get('module_pk')
        module_ = get_object_or_404(Module, id=module_pk_)
        self.filename = 'feedback_' + str(module_) + '.pdf'
        feedback_list = Feedback.objects.filter(module=module_, show=True)
        feedback_chart_ = FeedbackChart(module_pk=module_pk_)
        feedback_chart_.width = 550

        question_list = Question.objects.all()
        context['feedback_chart'] = feedback_chart_
        context['module'] = module_
        context['feedback_list'] = feedback_list
        context['question_list'] = question_list
        context['nb_reponses'] = Feedback.objects.filter(module=module_).count()
        context['nb_inscrits'] = module_.formation.inscriptions_actives().count()

        return context


class FeedbackListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/list.html'

    def test_func(self):
        return self.request.user.is_direction()

    def get_queryset(self, **kwargs):
        return Feedback.objects.filter(module=self.kwargs.get('module_pk')).exclude(
            Q(comment='') | Q(comment__isnull=True))

    def get_context_data(self, **kwargs):
        context = super(FeedbackListView, self).get_context_data(**kwargs)
        table = FeedbackTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['table'] = table
        context['titre'] = 'Liste des feedback'
        context['btn_list'] = {
            'Retour': reverse('module_list')
        }
        return context


class FeedbackPeriodeView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/feedback_periode_detail.html'

    def test_func(self):
        if int(self.kwargs.get('with_comments')) == 0:
            return True
        else:
            return self.request.user.is_direction()

    def get_context_data(self, **kwargs):
        context = super(FeedbackPeriodeView, self).get_context_data(**kwargs)
        periode_ = get_object_or_404(Periode, id=self.kwargs.get('periode_pk'))
        with_comments_ = self.kwargs.get('with_comments')
        module_list = Module.objects.filter(periode__periode=periode_,
                                            formation__annee_univ__annee_univ=self.kwargs.get('annee_univ_pk'))
        programme_list = Programme.objects.exclude(code__startswith='3').order_by('ordre')
        question_list = Question.objects.all().order_by('code')
        chart_list = {}
        feedback_list = {}

        for module_ in module_list:
            chart_list[module_.id] = FeedbackChart(module_pk=module_.id)
            if with_comments_ == '1':
                feedback_list[module_.id] = '<ul>'
                for feedback_ in Feedback.objects.filter(module=module_):
                    if feedback_.show and feedback_.comment:
                        feedback_list[module_.id] += '<li>' + feedback_.comment + '</li>'
                feedback_list[module_.id] += '</ul><br>'
        context['periode_'] = periode_
        context['module_list'] = module_list
        context['programme_list'] = programme_list
        context['question_list'] = question_list
        context['chart_list'] = chart_list
        context['feedback_list'] = feedback_list
        context['annee_univ'] = AnneeUniv.objects.get(annee_univ=self.kwargs.get('annee_univ_pk'))
        context['taux_reponse'] = {}
        for pgm in programme_list:
            nb_reponse = Reponse.objects.filter(feedback__module__formation__programme=pgm,
                                                feedback__module__formation__annee_univ__annee_univ=self.kwargs.get(
                                                    'annee_univ_pk'),
                                                feedback__module__periode__periode=self.kwargs.get('periode_pk')
                                                ).exclude(reponse='').distinct('feedback__inscription').count()
            context['taux_reponse'][pgm.code] = (
                nb_reponse,
                Inscription.objects.filter(formation__programme=pgm,
                                           formation__annee_univ__annee_univ=self.kwargs.get('annee_univ_pk')).exclude(
                    decision_jury='X').exclude(decision_jury__startswith='M').exclude(
                    decision_jury__startswith='F').exclude(inscription_periodes__groupe__isnull=True).count()
            )

        return context


class FeedbackUpdateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, UpdateView):
    model = Feedback
    fields = ['comment', 'show']
    template_name = 'scolar/update.html'
    success_message = "Le feedback a été modifié avec succès!"

    def test_func(self):
        return self.request.user.is_direction()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('feedback_list', kwargs={'module_pk': self.kwargs.get('module_pk')})
        return form


def feedback_etudiant_update_view(request, inscription_pk, periode_pk):
    # attention il faut évaluer les modules suivis au niveau des activités qui peuvent être différents des modules
    # prévus dans la programmation, par exemple un groupe SQ peut suivre un module TPRO des SL, mais dans son programme on prévoit un autre module TPRO des SQ
    inscription_ = Inscription.objects.get(id=inscription_pk)
    periodepgm_ = PeriodeProgramme.objects.get(id=periode_pk)
    inscription_periode_ = InscriptionPeriode.objects.get(inscription=inscription_, periodepgm=periode_pk)
    # TODO les questions ne sont pas adaptées au PFE, faut donc l'exclure et prévoir d'autres questions dans une maj
    groupe_section = inscription_periode_.groupe.section.groupes.all().filter(
        code__isnull=True).get()  # le groupe qui représente la section
    activites_suivies_list = Activite.objects.filter(cible__in=[inscription_periode_.groupe, groupe_section],
                                                     module__periode__periode=periodepgm_.periode,
                                                     module__matiere__pfe=False)
    module_list = []
    module_traite_list = []
    for activite_suivie in activites_suivies_list:
        if not activite_suivie.module.id in module_traite_list:
            module_traite_list.append(activite_suivie.module.id)
            if activite_suivie.module.matiere.mode_projet:
                question_list = Question.objects.exclude(projet_na=True).order_by('code')
            else:
                question_list = Question.objects.exclude(cours_na=True).order_by('code')
            module_list.append({
                'module': activite_suivie.module,
                'question_list': question_list
            })

    # if this is a POST request we need to process the form data

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:

        form = FeedbackUpdateForm(inscription_pk, periode_pk, request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                data = form.cleaned_data

                for module_info in module_list:
                    feedback_, created = Feedback.objects.update_or_create(module=module_info['module'],
                                                                           inscription=inscription_, defaults={
                            'module': module_info['module'],
                            'inscription': inscription_,
                            'comment': data[str(module_info['module'].id)],
                            'show': False
                        })

                    for question_ in module_info['question_list']:
                        reponse_, created = Reponse.objects.update_or_create(feedback=feedback_, question=question_,
                                                                             defaults={
                                                                                 'feedback': feedback_,
                                                                                 'question': question_,
                                                                                 'reponse': data[str(module_info[
                                                                                                         'module'].id) + '_' + question_.code]
                                                                             })
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: L'introduction de votre avis s'est terminé avec des erreurs. Merci de le signaler à l'administrateur")
                    return HttpResponseRedirect(reverse('etudiant_activite'))
            messages.success(request,
                             "Nous vous remercions. Votre avis sera pris en compte et transféré aux équipes pédagogiques")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('etudiant_activite'))
        else:
            messages.error(request,
                           'Votre formulaire contient des erreures. Merci de vérifier que vous avez bien remplis tous les onglets de ce formulaire.')
    # if a GET (or any other method) we'll create a blank form
    else:
        form = FeedbackUpdateForm(inscription_pk, periode_pk)
        messages.error(request,
                       "Merci de renseigner le formulaire pour chacun des modules. Autrement l'évaluation ne sera pas enregistrée!")
    return render(request, 'scolar/feedback_update_form.html', {'form': form, 'module_list': module_list})


class ModuleListView(LoginRequiredMixin, TemplateView):
    template_name = 'scolar/module_list.html'

    def get_queryset(self, **kwargs):
        return Module.objects.all()

    def get_context_data(self, **kwargs):
        context = super(ModuleListView, self).get_context_data(**kwargs)
        periode_list = Periode.objects.all().order_by('ordre')
        annee_univ_list = AnneeUniv.objects.all().order_by('annee_univ')
        filter_ = ModuleFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()
        table = ModuleFeedbackTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['periode_list'] = periode_list
        context['annee_univ_list'] = annee_univ_list
        return context


class ModuleCopyView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Module
    fields = ['matiere', 'formation', 'coordinateur', 'periode']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_module'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        module_ = get_object_or_404(Module, id=self.kwargs.get('module_pk'))
        form.fields['matiere'] = forms.ModelChoiceField(queryset=Matiere.objects.filter(code=module_.matiere.code),
                                                        initial=0)
        form.fields['formation'] = forms.ModelChoiceField(queryset=Formation.objects.filter(id=module_.formation.id),
                                                          initial=0)
        form.fields['periode'] = forms.ModelChoiceField(
            queryset=PeriodeProgramme.objects.filter(programme=module_.formation.programme.id), initial=0)
        form.helper.add_input(Submit('submit', 'Créer', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('planification_update',
                                   kwargs={'formation_pk': module_.formation.id, 'periode_pk': module_.periode.id})
        return form


class ModuleCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Module
    fields = ['matiere', 'formation', 'coordinateur', 'periode']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_module'
    success_message = "Le module a bien été créé."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        formation_ = get_object_or_404(Formation, id=self.kwargs.get('formation_pk'))
        periode_ = get_object_or_404(PeriodeProgramme, id=self.kwargs.get('periode_pk'))
        matieres_formation = Module.objects.filter(formation=formation_).values('matiere')
        form.fields['formation'] = forms.ModelChoiceField(queryset=Formation.objects.filter(id=formation_.id),
                                                          initial=0)
        form.fields['periode'] = forms.ModelChoiceField(queryset=PeriodeProgramme.objects.filter(id=periode_.id),
                                                        initial=0)
        # form.fields['matiere']=forms.ModelChoiceField(queryset=Matiere.objects.filter(id__in=matieres_formation).order_by('code'))
        form.fields['matiere'] = forms.ModelChoiceField(
            queryset=Matiere.objects.filter(matiere_ues__periode__programme=formation_.programme).order_by('code'))
        form.helper.add_input(Submit('submit', 'Créer', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('planification_update',
                                   kwargs={'formation_pk': formation_.id, 'periode_pk': periode_.id})
        return form


def module_evaluation_copy_view(request, module_pk):
    if not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SelectSingleModuleForm(request.POST)

        # check whether it's valid:
        if form.is_valid():
            try:
                dst_module_ = Module.objects.get(id=module_pk)
                form_data = form.cleaned_data
                src_module_ = form_data['module']
                for src_eval_ in src_module_.evaluations.all():
                    dst_eval_ = Evaluation.objects.create(
                        module=dst_module_,
                        ponderation=src_eval_.ponderation,
                        type=src_eval_.type
                    )
                    for src_eval_competence_ in src_eval_.competence_elements.all():
                        dst_eval_competence_ = EvaluationCompetenceElement.objects.create(
                            evaluation=dst_eval_,
                            competence_element=src_eval_competence_.competence_element,
                            ponderation=src_eval_competence_.ponderation,
                            commune_au_groupe=src_eval_competence_.commune_au_groupe
                        )

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: La copie de la fiche d'évaluation n'a pas réussit.")
                    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Sélectionner un Module'})
            messages.success(request, "La copie de la fiche d'évaluation s'est faite avec succès!")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('module_detail', kwargs={'pk': module_pk}))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = SelectSingleModuleForm()
        messages.info(request, "Indiquez le module à partir duqeul vous voulez copier la fiche d'évaluation.")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Sélectionner un Module'})


class ModuleUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = Module
    fields = ['coordinateur', 'periode', 'matiere']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_module'
    success_message = "Le module a bien été modifié."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['coordinateur'] = forms.ModelChoiceField(
            queryset=Enseignant.objects.all().order_by('nom', 'prenom'))
        form.fields['matiere'] = forms.ModelChoiceField(queryset=Matiere.objects.all().order_by('code'))
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('planification_update', kwargs={'formation_pk': self.kwargs.get('formation_pk'),
                                                                   'periode_pk': self.kwargs.get('periode_pk')})
        return form


class ModuleDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = Module
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_module'
    success_message = "Le module a bien été supprimé."

    def get_success_url(self):
        return reverse('planification_update', kwargs={'formation_pk': self.kwargs.get('formation_pk'),
                                                       'periode_pk': self.kwargs.get('periode_pk')})


@receiver(pre_delete, sender=Module)
def update_resultat_module_delete(sender, instance, **kwargs):
    # si un module suivi porte sur la même matière, basculer les résultats sur ce module
    module_similaire_list = Module.objects.filter(formation=instance.formation,
                                                  matiere__code=instance.matiere.code).exclude(id=instance.id)
    if module_similaire_list.exists():
        module_similaire = module_similaire_list[0]
        Resultat.objects.filter(module__matiere__code=instance.matiere.code,
                                inscription__formation=instance.formation).update(
            module=module_similaire
        )
        ModulesSuivis.objects.filter(module__matiere__code=instance.matiere.code,
                                     module__formation=instance.formation).exclude(module=instance).update(
            module=module_similaire)


class ModulesSuivisUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = ModulesSuivis
    fields = ['module', 'groupe']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_modulessuivis'
    success_message = "La modification du déroulement du module pour ce groupe a bien été effectuée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()

        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('planification_update', kwargs={'formation_pk': self.kwargs.get('formation_pk'),
                                                                   'periode_pk': self.kwargs.get('periode_pk')})
        return form


class ModulesSuivisCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = ModulesSuivis
    fields = ['module', 'groupe']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_modulessuivis'
    success_message = "L'affectation du module au groupe a bien été effectuée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        module_ = get_object_or_404(Module, id=self.kwargs.get('module_pk'))
        groupe_ = get_object_or_404(Groupe, id=self.kwargs.get('groupe_pk'))
        form.fields['module'] = forms.ModelChoiceField(queryset=Module.objects.filter(id=module_.id), initial=0)
        form.fields['groupe'] = forms.ModelChoiceField(queryset=Groupe.objects.filter(id=groupe_.id), initial=0)
        form.helper.add_input(Submit('submit', 'Créer', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('planification_update',
                                   kwargs={'formation_pk': module_.formation.id, 'periode_pk': module_.periode.id})
        return form


@receiver(post_save, sender=ModulesSuivis)
def update_resultat_module(sender, instance, created, **kwargs):
    Resultat.objects.filter(module__matiere=instance.module.matiere,
                            resultat_ue__inscription_periode__groupe=instance.groupe).update(
        module=instance.module
    )


class ModulesSuivisDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = ModulesSuivis
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_modulessuivis'
    success_message = "Le module a bien été retiré au groupe."

    def get_success_url(self):
        return reverse('planification_update', kwargs={'formation_pk': self.kwargs.get('formation_pk'),
                                                       'periode_pk': self.kwargs.get('periode_pk')})


@receiver(pre_delete, sender=ModulesSuivis)
def update_resultat_modulesuivis_delete(sender, instance, **kwargs):
    module_similaire_list = Module.objects.filter(formation=instance.module.formation,
                                                  matiere__code=instance.module.matiere.code)
    if module_similaire_list.exists():
        module_similaire = module_similaire_list[0]
        Resultat.objects.filter(module__matiere=instance.module.matiere,
                                resultat_ue__inscription_periode__groupe=instance.groupe).update(
            module=module_similaire
        )


class AbsenceChart(Chart):
    chart_type = 'bar'

    def __init__(self, etudiant_pk, periode_pk, *args, **kwargs):
        super(AbsenceChart, self).__init__(*args, **kwargs)
        self.labels = []
        self.data = []
        periode_ = PeriodeProgramme.objects.get(id=periode_pk)
        self.titre = "Nombre d'absences par matière : " + str(periode_.periode.code)
        try:
            inscription_etudiant = get_object_or_404(Inscription, etudiant=etudiant_pk,
                                                     formation__annee_univ__encours=True,
                                                     formation__programme=periode_.programme)
            groupe_etudiant = inscription_etudiant.groupe
            if groupe_etudiant:
                module_suivi_list = Resultat.objects.filter(inscription=inscription_etudiant,
                                                            module__periode=periode_pk)

                absence_list = AbsenceEtudiant.objects.filter(etudiant=etudiant_pk,
                                                              seance__activite__module__formation__annee_univ__encours=True,
                                                              seance__activite__module__periode=periode_pk)
                absence_etudiant_list = absence_list.values('etudiant',
                                                            'seance__activite__module__matiere__code').annotate(
                    nbr_abs=Count('seance__activite'))
                for absence in absence_etudiant_list:
                    self.labels.append(absence['seance__activite__module__matiere__code'])
                    self.data.append({'x': absence['seance__activite__module__matiere__code'], 'y': absence['nbr_abs']})
                for module_suivi in module_suivi_list:
                    if not module_suivi.module.matiere.code in self.labels:
                        self.labels.append(module_suivi.module.matiere.code)
                        self.data.append({'x': module_suivi.module.matiere.code, 'y': 0})
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: la génération du graphique des absences s'est terminée avec echec!")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return [DataSet(
            label=self.titre,
            data=self.data
        )]


class ProfileChart(Chart):
    chart_type = 'radar'
    options = {
        'scale': {
            'angleLines': {
                'display': True
            },
            'ticks': {
                'suggestedMin': 0,
                'suggestedMax': 20
            }
        }
    }

    def __init__(self, etudiant_pk, *args, **kwargs):
        super(ProfileChart, self).__init__(*args, **kwargs)
        self.labels = []
        self.data = []
        self.data_avg = []
        self.titre = "Profil par domaine de connaissance"
        try:
            # construction du profile: moyenne par domaine de connaissance
            etudiant_ = Etudiant.objects.get(matricule=etudiant_pk)
            resultat_list = Resultat.objects.filter(Q(inscription__etudiant=etudiant_) & (
                        Q(inscription__decision_jury='A') | Q(inscription__decision_jury='AR')))
            ddc_moy_list = resultat_list.values('module__matiere__ddc__intitule').annotate(moy_ddc=Avg('moy'))

            for ddc_moy in ddc_moy_list:
                self.labels.append(ddc_moy['module__matiere__ddc__intitule'])
                self.data.append(round(ddc_moy['moy_ddc'], 2))
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request, "ERREUR: lors dde la génération du graphique du profil.")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return [DataSet(
            label=self.titre,
            data=self.data
        )]


class EtudiantEffectifsChart(Chart):
    chart_type = 'bar'
    options = {
        'scales': {
            'xAxes': [{
                'stacked': True
            }],
            'yAxes': [{
                'stacked': True,
                'offset': True
            }]
        }
    }

    def __init__(self, ratio_, *args, **kwargs):
        super(EtudiantEffectifsChart, self).__init__(*args, **kwargs)
        self.labels = []
        self.data = []
        try:
            inscription_list = Inscription.objects.filter(formation__annee_univ__encours=True).exclude(
                Q(inscription_periodes__groupe__isnull=True) | Q(decision_jury='X')).order_by(
                'formation__programme__ordre')
            fille_count = Count('etudiant', filter=Q(etudiant__sexe='F'))
            garcon_count = Count('etudiant', filter=Q(etudiant__sexe='M'))
            total_count = Count('etudiant')
            inscription_programme_data = inscription_list.values('formation__programme__code').annotate(
                fille=fille_count).annotate(garcon=garcon_count).annotate(total=total_count)

            sexe_list = [
                {
                    'label': 'fille',
                    'sexe': 'F',
                    'color': (255, 120, 255)
                },
                {
                    'label': 'garcon',
                    'sexe': 'M',
                    'color': (0, 0, 255)
                },
            ]

            for sexe in sexe_list:
                data_ = []

                for programme_ in inscription_programme_data:
                    if ratio_:
                        data_.append(round(programme_[sexe['label']] / programme_['total'], 2))
                    else:
                        data_.append(programme_[sexe['label']])
                    if not programme_['formation__programme__code'] in self.labels:
                        self.labels.append(programme_['formation__programme__code'])
                dataset = DataSet(label=sexe['sexe'], data=data_, color=sexe['color'])

                self.data.append(dataset)
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request, "ERREUR: lors de la génération du graphique des effectifs étudiants")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return self.data


class AbsenceLiveChart(Chart):
    chart_type = 'line'

    def __init__(self, *args, **kwargs):
        super(AbsenceLiveChart, self).__init__(*args, **kwargs)
        self.labels = []
        self.data = []
        self.titre = "Nombre d'absences par jour"
        try:
            absence_list = AbsenceEtudiant.objects.filter(
                seance__date__gt=datetime.date.today() - datetime.timedelta(days=5 * 30)).order_by('seance__date')
            absence_data = absence_list.values('seance__date').annotate(absence_count=Count('etudiant'))

            for absence_jour in absence_data:
                self.labels.append(absence_jour['seance__date'])
                self.data.append(absence_jour['absence_count'])
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request, "ERREUR: lors de la génération du graphique du nombre d'absences par jour")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return [DataSet(
            label=self.titre,
            data=self.data
        )]


class EtudiantWilayaResidenceChart(Chart):
    chart_type = 'pie'
    options = {
        'legend': {
            'display': False,
        }
    }

    def __init__(self, annee_univ_pk, *args, **kwargs):
        super(EtudiantWilayaResidenceChart, self).__init__(*args, **kwargs)
        self.labels = []
        self.data = []
        self.colors = []
        try:
            inscriptions_encours = Inscription.objects.filter(formation__annee_univ__annee_univ=annee_univ_pk).exclude(
                Q(decision_jury='X') | Q(inscription_periodes__groupe__isnull=True) | Q(
                    decision_jury__startswith='F')).values('etudiant')
            # les étudiants en master ont une double inscription
            etudiants_encours_aggregate = Etudiant.objects.filter(matricule__in=inscriptions_encours).distinct().values(
                'wilaya_residence__nom').annotate(nb_etudiants=Count('matricule')).order_by('nb_etudiants')

            for wilaya_aggregate in etudiants_encours_aggregate:
                if wilaya_aggregate['wilaya_residence__nom'] == None:
                    self.labels.append("Non disponible")
                else:
                    self.labels.append(wilaya_aggregate['wilaya_residence__nom'])
                self.data.append(wilaya_aggregate['nb_etudiants'])
                self.colors.append("#%06x" % random.randint(0, 0xFFFFFF))
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération du graphique d'aggrégat des Wilayas de résidence.")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return [DataSet(data=self.data, backgroundColor=self.colors)]


class EtudiantInterneChart(Chart):
    chart_type = 'pie'

    def __init__(self, annee_univ_pk, *args, **kwargs):
        super(EtudiantInterneChart, self).__init__(*args, **kwargs)
        self.labels = []
        self.data = []
        self.colors = []
        try:
            inscriptions_encours = Inscription.objects.filter(formation__annee_univ__annee_univ=annee_univ_pk).exclude(
                Q(decision_jury='X') | Q(inscription_periodes__groupe__isnull=True) | Q(
                    decision_jury__startswith='F')).values('etudiant')
            # les étudiants en master ont une double inscription
            etudiants_encours_aggregate = Etudiant.objects.filter(matricule__in=inscriptions_encours).distinct().values(
                'interne').annotate(nb_etudiants=Count('matricule')).order_by('nb_etudiants')
            total = Etudiant.objects.filter(matricule__in=inscriptions_encours).distinct().count()
            for interne_aggregate in etudiants_encours_aggregate:
                self.labels.append("Internes" if interne_aggregate['interne'] else "Externes")
                self.data.append(interne_aggregate['nb_etudiants'])
                # , round(float(interne_aggregate['nb_etudiants'])/float(total)*100,2))
                self.colors.append("#%06x" % random.randint(0, 0xFFFFFF))
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération du graphique d'aggrégat des Wilayas de résidence.")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return [DataSet(data=self.data, backgroundColor=self.colors)]


class DashboardEtudiantView(LoginRequiredMixin, TemplateView):
    template_name = 'scolar/dashboard_etudiant.html'

    def get_context_data(self, **kwargs):
        context = super(DashboardEtudiantView, self).get_context_data(**kwargs)
        context['effectifs_par_sexe_chart'] = EtudiantEffectifsChart(False)
        context['effectifs_ratio_par_sexe_chart'] = EtudiantEffectifsChart(True)
        context['absence_live_chart'] = AbsenceLiveChart()
        annee_univ_encours_pk = AnneeUniv.objects.get(encours=True).annee_univ
        context['effectifs_wilaya_residence'] = EtudiantWilayaResidenceChart(annee_univ_encours_pk)
        inscriptions_encours = Inscription.objects.filter(
            formation__annee_univ__annee_univ=annee_univ_encours_pk).exclude(
            Q(decision_jury='X') | Q(inscription_periodes__groupe__isnull=True) | Q(
                decision_jury__startswith='F')).values('etudiant')
        # les étudiants en master ont une double inscription
        etudiants_encours_aggregate = Etudiant.objects.filter(matricule__in=inscriptions_encours).distinct().values(
            'wilaya_residence__nom').annotate(nb_etudiants=Count('matricule')).order_by('-nb_etudiants')
        context['wilayas_aggregate'] = etudiants_encours_aggregate
        context['total'] = etudiants_encours_aggregate = Etudiant.objects.filter(
            matricule__in=inscriptions_encours).distinct().count()
        context['interne_chart'] = EtudiantInterneChart(annee_univ_encours_pk)
        return context


class FormationDecisionJuryChart(Chart):
    chart_type = 'pie'

    def __init__(self, formation_pk, *args, **kwargs):
        super(FormationDecisionJuryChart, self).__init__(*args, **kwargs)
        self.labels = ['En cours', 'Admis', 'Admis avec Rachat', 'Redouble', 'Non Admis', 'Abandon', 'Maladie']
        try:
            formation_ = Formation.objects.get(id=formation_pk)
            formation_aggregate = formation_.aggregate_decision_jury()

            self.data = []
            if formation_aggregate:
                if formation_aggregate['total'] != 0:
                    self.data.append(round(formation_aggregate['encours'] / formation_aggregate['total'], 2))
                    self.data.append(round(formation_aggregate['admis'] / formation_aggregate['total'], 2))
                    self.data.append(round(formation_aggregate['admis_rachat'] / formation_aggregate['total'], 2))
                    self.data.append(round(formation_aggregate['redouble'] / formation_aggregate['total'], 2))
                    self.data.append(round(formation_aggregate['non_admis'] / formation_aggregate['total'], 2))
                    self.data.append(round(formation_aggregate['abandon'] / formation_aggregate['total'], 2))
                    self.data.append(round(formation_aggregate['maladie'] / formation_aggregate['total'], 2))

            self.colors = ['#c2c2d6', '#009933', '#66ff66', '#ff9933', '#ff0000', '#000000', '#3333cc']
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération du graphique d'aggrégat des décisions de jury.")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return [DataSet(data=self.data, backgroundColor=self.colors)]


class ProgrammeAvgDecisionJuryChart(Chart):
    chart_type = 'bar'
    options = {
        'scales': {
            'xAxes': [{
                'stacked': True
            }],
            'yAxes': [{
                'stacked': True,
                'offset': True
            }]
        }
    }

    def __init__(self, *args, **kwargs):
        super(ProgrammeAvgDecisionJuryChart, self).__init__(*args, **kwargs)
        self.labels = []
        self.data = []
        try:
            programme_data = {}
            for programme_ in Programme.objects.all().order_by('ordre'):
                aggregate_ = programme_.aggregate_avg_decision_jury()
                if aggregate_:
                    programme_data[programme_.code] = aggregate_

            decision_list = [
                {
                    'label': 'Succès %: Admis et Rachat',
                    'decision': 'success',
                    'color': (0, 153, 51)
                },
                {
                    'label': 'Echec %: Réorientés et Abandons',
                    'decision': 'echec',
                    'color': (255, 51, 0)
                },
                {
                    'label': 'Seconde chance %: Redoublants et Congés de Maladie',
                    'decision': 'refaire',
                    'color': (255, 255, 102)
                },

            ]

            for decision in decision_list:
                data_ = []
                for code in programme_data.keys():
                    data_.append(programme_data[code][decision['decision']])
                    if not code in self.labels:
                        self.labels.append(code)
                dataset = DataSet(label=decision['label'], data=data_, color=decision['color'])

                self.data.append(dataset)
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération du graphique des aggrégats de décision de jury par programme")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return self.data


class DashboardFormationView(LoginRequiredMixin, TemplateView):
    template_name = 'scolar/dashboard_formation.html'

    def get_context_data(self, **kwargs):
        context = super(DashboardFormationView, self).get_context_data(**kwargs)
        annee_univ_qs = AnneeUniv.objects.all().order_by('annee_univ')
        annee_univ_list = []
        for annee_univ_ in annee_univ_qs:
            element = {
                'annee_univ': annee_univ_,
                'formation_list': []
            }
            formation_list = Formation.objects.filter(annee_univ=annee_univ_).order_by('programme__ordre')
            for formation_ in formation_list:
                element['formation_list'].append({
                    'formation': formation_,
                    'chart': FormationDecisionJuryChart(formation_.id)
                })
            annee_univ_list.append(element)
        context['annee_univ_list'] = annee_univ_list
        context['programme_avg_chart'] = ProgrammeAvgDecisionJuryChart()
        context['programme_list'] = Programme.objects.all().order_by('ordre')
        context['decision_list'] = ['admis', 'admis_rachat', 'success', 'non_admis', 'abandon', 'echec', 'redouble',
                                    'maladie', 'refaire', 'total']
        return context


class AbsenceEnseignantLiveChart(Chart):
    chart_type = 'line'

    def __init__(self, *args, **kwargs):
        super(AbsenceEnseignantLiveChart, self).__init__(*args, **kwargs)
        self.labels = []
        self.data = []
        self.titre = "Nombre d'absences par jour"
        try:
            absence_list = AbsenceEnseignant.objects.filter(
                seance__activite__module__formation__annee_univ__encours=True,
                seance__date__gt=datetime.date.today() - datetime.timedelta(days=5 * 30))
            absence_data = absence_list.values('seance__date').annotate(absence_count=Count('enseignant'))

            for absence_jour in absence_data:
                self.labels.append(absence_jour['seance__date'])
                self.data.append(absence_jour['absence_count'])
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération du graphique du nombre d'absences enseignants par jour")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return [DataSet(
            label=self.titre,
            data=self.data
        )]


class EnseignantChargeChart(Chart):
    chart_type = 'pie'

    def __init__(self, *args, **kwargs):
        super(EnseignantChargeChart, self).__init__(*args, **kwargs)
        self.labels = ['<30%', '[30%-40%]', '[40%-50%]', '[50%-60%]', '[60%-70%]', '[70%-80%]', '[80%-90%]',
                       '[90%-100%]', '>100%']
        try:
            charge_list = Charge.objects.filter(annee_univ__encours=True, realisee_par__situation='A').values(
                'realisee_par').annotate(ratio=
            Case(
                When(realisee_par__statut='V', then=Value(1)),
                When(realisee_par__statut='P', then=Sum(
                    Case(
                        When(repeter_chaque_semaine=True,
                             then=ExpressionWrapper(F('vh_eq_td'), output_field=DecimalField()) * 15.0),
                        When(repeter_chaque_semaine=False,
                             then=ExpressionWrapper(F('vh_eq_td'), output_field=DecimalField()))
                    )
                ) / F('realisee_par__charge_statut'))

            )
            )
            self.data = []
            if charge_list.count() != 0:
                self.data.append(round(charge_list.filter(ratio__lt=Value(0.3)).count() / charge_list.count(), 2))
                self.data.append(round(charge_list.filter(ratio__gte=Value(0.3)).filter(
                    ratio__lt=Value(0.4)).count() / charge_list.count(), 2))
                self.data.append(round(charge_list.filter(ratio__gte=Value(0.4)).filter(
                    ratio__lt=Value(0.5)).count() / charge_list.count(), 2))
                self.data.append(round(charge_list.filter(ratio__gte=Value(0.5)).filter(
                    ratio__lt=Value(0.6)).count() / charge_list.count(), 2))
                self.data.append(round(charge_list.filter(ratio__gte=Value(0.6)).filter(
                    ratio__lt=Value(0.7)).count() / charge_list.count(), 2))
                self.data.append(round(charge_list.filter(ratio__gte=Value(0.7)).filter(
                    ratio__lt=Value(0.8)).count() / charge_list.count(), 2))
                self.data.append(round(charge_list.filter(ratio__gte=Value(0.8)).filter(
                    ratio__lt=Value(0.9)).count() / charge_list.count(), 2))
                self.data.append(round(charge_list.filter(ratio__gte=Value(0.9)).filter(
                    ratio__lt=Value(1.0)).count() / charge_list.count(), 2))
                self.data.append(round(charge_list.filter(ratio__gte=Value(1.0)).count() / charge_list.count(), 2))

            self.colors = ['#AA6968', '#808080', '#A9A9A9', '#C0C0C0', '#D3D3D3', '#809080', '#A959A9', '#C0B0C0',
                           '#D2D3D3']
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request, "ERREUR: lors de la génération du graphique de répartition des charges")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return [DataSet(data=self.data, backgroundColor=self.colors)]


class EnseignantEffectifsChart(Chart):
    chart_type = 'bar'
    options = {
        'scales': {
            'xAxes': [{
                'stacked': True
            }],
            'yAxes': [{
                'stacked': True,
                'offset': True
            }]
        }
    }

    def __init__(self, ratio_, *args, **kwargs):
        super(EnseignantEffectifsChart, self).__init__(*args, **kwargs)
        self.labels = []
        self.data = []
        try:
            fille_count = Count('id', filter=Q(sexe='F'))
            garcon_count = Count('id', filter=Q(sexe='M'))
            total_count = Count('id')
            enseignant_data = Enseignant.objects.exclude(situation='R').values('statut').annotate(
                Femme=fille_count).annotate(Homme=garcon_count).annotate(total=total_count)

            sexe_list = [
                {
                    'label': 'Femme',
                    'sexe': 'F',
                    'color': (255, 120, 255)
                },
                {
                    'label': 'Homme',
                    'sexe': 'M',
                    'color': (0, 0, 255)
                },
            ]

            for sexe in sexe_list:
                data_ = []
                for statut_ in enseignant_data:
                    if ratio_:
                        data_.append(round(statut_[sexe['label']] / statut_['total'], 2))
                    else:
                        data_.append(statut_[sexe['label']])
                    if not dict(STATUT)[statut_['statut']] in self.labels:
                        self.labels.append(dict(STATUT)[statut_['statut']])
                dataset = DataSet(label=sexe['label'], data=data_, color=sexe['color'])

                self.data.append(dataset)
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request, "ERREUR: lors de la génération du graphique des effectifs enseignants")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return self.data


class EnseignantGradeChart(Chart):
    chart_type = 'pie'

    def __init__(self, *args, **kwargs):
        self.labels = []
        self.data = []
        super(EnseignantGradeChart, self).__init__(*args, **kwargs)
        for grade_ in dict(GRADE).keys():
            self.labels.append(dict(GRADE)[grade_])
        try:
            enseignant_aggregate = Enseignant.objects.filter(situation='A').exclude(
                Q(statut='V') | Q(statut='A')).values('grade').annotate(grade_count=Count('id'))

            self.data = []

            for grade_ in dict(GRADE).keys():
                for element in enseignant_aggregate:
                    if element['grade'] == grade_:
                        self.data.append(element['grade_count'])
            # rajouter le cas grade inconuu
            for element in enseignant_aggregate:
                if element['grade'] == None:
                    self.data.append(element['grade_count'])
                    self.labels.append('Non disponible')
            self.colors = ['#c2c2d6', '#009933', '#66ff66', '#ff9933', '#ff0000', '#3333cc']
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération du graphique d'aggrégat des grades des enseignants.")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return [DataSet(data=self.data, backgroundColor=self.colors)]


class DashboardEnseignantView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/dashboard_enseignant.html'

    def test_func(self):
        return self.request.user.is_top_management()

    def get_context_data(self, **kwargs):
        context = super(DashboardEnseignantView, self).get_context_data(**kwargs)
        enseignant_aggregate = Enseignant.objects.filter(situation='A').exclude(Q(statut='V') | Q(statut='A')).values(
            'grade').annotate(grade_count=Count('id'))
        total = Enseignant.objects.filter(situation='A').exclude(Q(statut='V') | Q(statut='A')).count()
        grade_count_list = {}
        for grade_ in dict(GRADE).keys():
            for element in enseignant_aggregate:
                if element['grade'] == grade_:
                    grade_count_list[grade_] = element['grade_count']
        for element in enseignant_aggregate:
            if element['grade'] == None:
                grade_count_list['Non disponible'] = element['grade_count']
        context['total'] = total
        context['grade_count_list'] = grade_count_list
        context['effectifs_par_sexe_chart'] = EnseignantEffectifsChart(False)
        context['effectifs_ratio_par_sexe_chart'] = EnseignantEffectifsChart(True)
        context['enseignant_charge_chart'] = EnseignantChargeChart()
        context['enseignant_absence_live_chart'] = AbsenceEnseignantLiveChart()
        context['enseignant_grade_chart'] = EnseignantGradeChart
        return context


class EtudiantDetailView(UserPassesTestMixin, DetailView):
    model = Etudiant
    template_name = 'scolar/etudiant_detail.html'

    def test_func(self):
        etudiant_ = get_object_or_404(Etudiant, matricule=self.kwargs.get('pk'))
        if etudiant_.public_profile:
            return True
        else:
            return self.request.user.is_staff_or_student_himself(etudiant_.matricule)

    def get_context_data(self, **kwargs):
        context = super(EtudiantDetailView, self).get_context_data(**kwargs)
        etudiant_ = context['object']
        private = False
        if not self.request.user.is_authenticated:
            private = True
        else:
            private = not self.request.user.is_staff_or_student_himself(etudiant_.matricule)
        context['private'] = private
        exclude_ = []
        if private:
            exclude_.append('detail')
        if not self.request.user.is_authenticated:
            exclude_.append('edit')
        elif not (self.request.user.is_direction()):
            exclude_.append('edit')
        parcours = InscriptionEtudiantTable(
            Inscription.objects.filter(etudiant=etudiant_).order_by('formation__annee_univ'), exclude=exclude_)
        RequestConfig(self.request).configure(parcours)
        context['parcours'] = parcours
        profile_chart = ProfileChart(etudiant_pk=self.kwargs.get('pk'))
        context['profile_chart'] = profile_chart
        context['decision_jury'] = dict(DECISIONS_JURY)
        try:
            inscription_encours_list = Inscription.objects.filter(etudiant=etudiant_,
                                                                  formation__annee_univ__encours=True)
        except Inscription.DoesNotExist:
            pass
        else:
            # générer un chart pour chaque periode (semestre)
            absence_chart_list = []
            for inscription_encours in inscription_encours_list:
                for periode in inscription_encours.formation.programme.periodes.all():
                    absence_chart_list.append(AbsenceChart(etudiant_pk=self.kwargs.get('pk'), periode_pk=periode.id))
            context['absence_chart_list'] = absence_chart_list

        return context


class EtudiantUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UserPassesTestMixin,
                         UpdateView):
    model = Etudiant
    fields = ['nom', 'nom_a', 'prenom', 'prenom_a', 'sexe', 'photo', 'date_naissance', 'wilaya_naissance',
              'lieu_naissance', 'lieu_naissance_a', 'wilaya_residence', 'commune_residence', 'addresse_principale',
              'interne', 'residence_univ', 'tel', 'numero_securite_sociale', 'activite_extra', 'tuteur']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_etudiant'
    success_message = "Le dossier étudiant a été modifié avec succès!"

    def test_func(self):
        return self.request.user.is_staff_only()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['date_naissance'] = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS,
                                                        widget=DatePickerInput(format='%d/%m/%Y'))
        form.fields[
            'photo'].help_text = "Si vous voulez changer de photo, merci de déposer ici un scan d'une photo d'identité. Taille maximale 1M."
        form.fields[
            'numero_securite_sociale'].help_text = "Merci d'indiquer le numéro figurant sur l'ATS ou carte CHIFA."
        form.fields['wilaya_naissance'] = forms.ModelChoiceField(
            queryset=Wilaya.objects.all().order_by('nom'),
            label=u"Wilaya de naissance",
            widget=ModelSelect2Widget(
                model=Wilaya,
                search_fields=['nom__icontains', ],
            ),
            help_text="Choisir une wilaya. Tapez deux espaces pour avoir toute la liste.",
        )

        form.fields['wilaya_residence'] = forms.ModelChoiceField(
            queryset=Wilaya.objects.all().order_by('nom'),
            label=u"Wilaya de résidence principale",
            widget=ModelSelect2Widget(
                model=Wilaya,
                search_fields=['nom__icontains', ],
            ),
            help_text="Choisir une wilaya. Tapez deux espaces pour avoir toute la liste.",
        )
        form.fields['commune_residence'] = forms.ModelChoiceField(
            queryset=Commune.objects.all().order_by('nom'),
            label=u"Commune de résidence principale",
            widget=ModelSelect2Widget(
                model=Commune,
                search_fields=['nom__icontains', ],
                dependent_fields={'wilaya_residence': 'wilaya'},
            ),
            help_text="Choisir une commune. Tapez deux espaces pour avoir toute la liste.",
        )

        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('etudiant_detail', kwargs={'pk': str(self.kwargs.get('pk'))})
        return form


class EtudiantProfileUpdateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, UpdateView):
    model = Etudiant
    fields = ['public_profile', 'github', 'linkdin', 'activite_extra', ]
    template_name = 'scolar/update.html'
    success_message = "Votre dossier a été mis à jour avec succès!"

    def test_func(self):
        if self.request.user.etudiant.matricule == self.kwargs.get('pk'):
            messages.info(self.request, "Utilisez ce formulaire pour rendre votre profile visible sur Talents Finder!")
            messages.info(self.request,
                          "Si vous voulez rajouter des activités extra-scolaire, merci d'en faire la demande à votre tuteur ou chef de département.")
            return True
        else:
            return False

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['linkdin'] = forms.URLField(label='Linkedin', required=False)
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('etudiant_detail', kwargs={'pk': str(self.kwargs.get('pk'))})
        return form


class EtudiantActiviteExtraUpdateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, UpdateView):
    model = Etudiant
    fields = ['activite_extra', ]
    template_name = 'scolar/update.html'
    success_message = "Le dossier de votre étudiant a été mis à jour avec succès!"

    def test_func(self):
        if self.request.user.is_tuteur(self.kwargs.get('pk')):
            messages.info(self.request, "Utilisez ce formulaire pour rajouter des activités extra-scolaires.")
            messages.info(self.request,
                          "Merci de se limiter aux activités officiellement reconnues à l'école dans le cadre de la vie associative et sportive.")
            messages.warning(self.request,
                             "Merci de vérifier la véracité des informations auprès du service des activités associatives et sportives.")
            return True
        else:
            return False

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('tutorat_list')
        return form


class EtudiantSituationCertificatePDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/situation_certificate_pdf.html'

    def test_func(self):
        etudiant_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk')).etudiant
        return self.request.user.is_staff_or_student_himself(etudiant_.matricule)

    def get_context_data(self, **kwargs):
        context = super(EtudiantSituationCertificatePDFView, self).get_context_data(**kwargs)
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        self.filename = str(inscription_.etudiant) + '_Situation_Certificate.pdf'
        context['inscription'] = inscription_
        context['today'] = datetime.date.today()

        return context


class EtudiantAttestationEtudesFrancaisPDFView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/attestation_etudes_francais_pdf.html'
    cmd_options = {
        'orientation': 'Portrait',
        'page-size': 'A5',
    }

    def test_func(self):
        etudiant_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk')).etudiant
        return self.request.user.is_staff_or_student_himself(etudiant_.matricule)

    def get_context_data(self, **kwargs):
        context = super(EtudiantAttestationEtudesFrancaisPDFView, self).get_context_data(**kwargs)
        inscription_ = Inscription.objects.get(id=self.kwargs.get('inscription_pk'))
        self.filename = str(inscription_.etudiant) + '_Etudes_Francais.pdf'
        context['inscription'] = inscription_
        context['today'] = datetime.date.today()

        return context


class EtudiantDocumentsListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/etudiant_documents.html'

    def test_func(self):
        return self.request.user.is_staff_or_student_himself(self.kwargs.get('etudiant_pk'))

    def get_context_data(self, **kwargs):
        context = super(EtudiantDocumentsListView, self).get_context_data(**kwargs)
        etudiant_ = Etudiant.objects.get(matricule=self.kwargs.get('etudiant_pk'))
        parcours = InscriptionEtudiantDocumentsTable(
            Inscription.objects.filter(etudiant=etudiant_).order_by('formation__annee_univ'),
            exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(parcours)
        context['table'] = parcours

        documents = {}
        inscription_encours_list = Inscription.objects.filter(etudiant=etudiant_.matricule,
                                                              formation__annee_univ__encours=True).exclude(
            decision_jury='X')
        for inscription_ in inscription_encours_list:
            documents['Situation Certificate ' + str(inscription_.formation)] = reverse("situation_certificate_pdf",
                                                                                        kwargs={
                                                                                            'inscription_pk': inscription_.id})
            documents["Attestation d'études en français " + str(inscription_.formation)] = reverse(
                "attestation_etudes_francais_pdf", kwargs={'inscription_pk': inscription_.id})
        for diplome in Diplome.objects.all():
            inscriptions = Inscription.objects.filter(etudiant=self.kwargs.get('etudiant_pk'),
                                                      formation__programme__diplome=diplome)
            if inscriptions.exists():
                documents["Relevé de Notes Global du Diplome " + str(diplome)] = reverse('releve_notes_global_pdf',
                                                                                         kwargs={
                                                                                             'etudiant_pk': self.kwargs.get(
                                                                                                 'etudiant_pk'),
                                                                                             'diplome_pk': diplome.id})
        context['documents'] = documents
        context['titre'] = 'Documents de ' + str(etudiant_)
        return context


def inscription_update_view(request, pk):
    inscription_ = get_object_or_404(Inscription, id=pk)
    if not (request.user.is_direction()):
        messages.error(request, "Vous n'avez pas la permission d'accès à cette fonction.")
        return redirect('/accounts/login/?next=%s' % request.path)
    elif inscription_.formation.archive:
        messages.error(request, "Cette formation est archivée, il n'est pas possible de modifier cette inscription.")
        return redirect('inscription_list')

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = InscriptionUpdateForm(pk, request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                form_data = form.cleaned_data

                inscription_.decision_jury = form_data['decision_jury']
                inscription_.save(update_fields=['decision_jury'])
                for inscription_periode_ in inscription_.inscription_periodes.all():
                    key_ = 'groupe_' + str(inscription_periode_.id)
                    inscription_periode_.groupe = form_data[key_]
                    inscription_periode_.save()

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: La modification de l'inscription s'est terminée avec des erreurs.")
                    render(request, 'scolar/import.html', {'form': form, 'titre': 'Modification d\'une Inscription'})
            messages.success(request, "La modification de l'inscription a été réalisée avec succès!")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('etudiant_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = InscriptionUpdateForm(pk)
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Modification d\'une Inscription'})


class InscriptionDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'scolar.delete_inscription'
    model = Inscription
    template_name = 'scolar/delete.html'
    success_message = "L'inscription a bien été supprimée."

    def get_success_url(self):
        return reverse('etudiant_detail', kwargs={'pk': self.kwargs.get('etudiant_pk')})


class InscriptionCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Inscription
    fields = ['etudiant', 'formation']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_inscription'
    success_message = "La nouvelle inscription a été ajoutée avec succès!"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['etudiant'] = forms.ModelChoiceField(
            queryset=Etudiant.objects.filter(matricule=self.kwargs.get('etudiant_pk')), initial=0)
        form.fields['formation'] = forms.ModelChoiceField(
            queryset=Formation.objects.all().order_by('-annee_univ__annee_univ', 'programme__ordre'), required=True)
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('etudiant_detail', kwargs={'pk': self.kwargs.get('etudiant_pk')})
        return form


class InscriptionListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'scolar.view_inscription'
    template_name = 'scolar/filter_list.html'

    def get_queryset(self, **kwargs):
        return Inscription.objects.filter(formation__annee_univ__encours=True)

    def get_context_data(self, **kwargs):
        context = super(InscriptionListView, self).get_context_data(**kwargs)
        filter_ = InscriptionFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()
        table = InscriptionTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['back'] = reverse('home')
        btn_list = {}
        if self.request.user.is_direction():
            btn_list['Import Inscriptions'] = reverse('inscriptions_import')
            btn_list['Import Affectations Groupes'] = reverse('import_affectation_groupe')
        if self.request.user.is_stage():
            btn_list['Import Affectations PFE'] = reverse('import_affectation_pfe')
        context['btn_list'] = btn_list
        context['titre'] = 'Etudiants Inscrits Année en Cours'
        return context


def inscription_annee_suivante_view(request, formation_pk):
    try:
        formation_ = Formation.objects.get(id=formation_pk)
        formation_.archive = True
        formation_.save(update_fields=['archive'])
        # submit as background task
        # t = threading.Thread(target=task_note_update,args=[form, module_, groupe_, request.user])
        # t.setDaemon(True)
        # t.start()
        # messages.info(request, "Votre demande d'enregistrement des notes a été prise en compte. Une notification vous sera transmise.")

        # inscrire les maladies et redoublants dans la même formation année suivante
        formation_idem_annee_suivante = formation_.formation_idem_annee_suivante()
        inscription_non_admis_list = Inscription.objects.filter(
            Q(formation=formation_) & (Q(decision_jury='R') | Q(decision_jury__startswith='M') | Q(decision_jury='AJ')))
        for inscription_ in inscription_non_admis_list:
            # indiquer les modules acquis
            if inscription_.decision_jury == 'R':
                for resultat_ in Resultat.objects.filter(inscription=inscription_):
                    if resultat_.moy_post_delib >= 10:
                        resultat_.acquis = True
                    else:
                        resultat_.acquis = False
                    resultat_.save(update_fields=['acquis'])
            nouvelle_inscription_, created = Inscription.objects.update_or_create(etudiant=inscription_.etudiant,
                                                                                  formation=formation_idem_annee_suivante,
                                                                                  defaults={
                                                                                      'etudiant': inscription_.etudiant,
                                                                                      'formation': formation_idem_annee_suivante,
                                                                                  })
            # créer inscription_periodes selon le programme
            for periode_ in formation_idem_annee_suivante.programme.periodes.all():
                InscriptionPeriode.objects.update_or_create(inscription=nouvelle_inscription_, periodepgm=periode_,
                                                            defaults={
                                                                'inscription': nouvelle_inscription_,
                                                                'periodepgm': periode_,
                                                            })

        formation_sup_annee_suivante = formation_.formation_sup_annee_suivante()
        if formation_sup_annee_suivante == None:

            # Ce cas correspond à l'année suivante qui requière le choix de spécialité
            return HttpResponseRedirect(reverse('inscriptions_import'))
        else:
            # inscrire les admis dans formation_sup_annee_suivante
            inscription_admis_list = Inscription.objects.filter(
                Q(formation=formation_) & (Q(decision_jury='A') | Q(decision_jury='AR')))
            for inscription_ in inscription_admis_list:
                nouvelle_inscription_, created = Inscription.objects.update_or_create(etudiant=inscription_.etudiant,
                                                                                      formation=formation_sup_annee_suivante,
                                                                                      defaults={
                                                                                          'etudiant': inscription_.etudiant,
                                                                                          'formation': formation_sup_annee_suivante,
                                                                                      })
                # créer inscription_periodes selon le programme
                for periode_ in formation_sup_annee_suivante.programme.periodes.all():
                    InscriptionPeriode.objects.update_or_create(inscription=nouvelle_inscription_, periodepgm=periode_,
                                                                defaults={
                                                                    'inscription': nouvelle_inscription_,
                                                                    'periodepgm': periode_,
                                                                })

        messages.success(request, "Les inscriptions vers l'année suivante ont été réalisées avec succès!")
        return HttpResponseRedirect(reverse('deliberation_detail', kwargs={'formation_pk': formation_pk, }))
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: lors des inscriptions vers l'année suivante. Merci de le signaler à l'administrateur")


class EnseignantListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'scolar/filter_list.html'
    permission_required = 'scolar.view_enseignant'

    def get_queryset(self, **kwargs):
        return Enseignant.objects.all().order_by('nom', 'prenom')

    def get_context_data(self, **kwargs):
        context = super(EnseignantListView, self).get_context_data(**kwargs)
        filter_ = EnseignantFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()
        table = EnseignantTable(filter_.qs, exclude=exclude_columns(self.request.user))

        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['titre'] = 'Liste des enseignants'
        context['back'] = reverse('home')
        if self.request.user.has_perm('scolar.add_enseignant'):
            context['create_url'] = reverse('enseignant_create')
            context['create_btn'] = 'Enseignant'
            context['import_url'] = reverse('enseignant_import')
            context['import_btn'] = 'Importer'

        return context


class EnseignantEDTView(TemplateView):
    template_name = 'scolar/enseignant_edt.html'

    def get_context_data(self, **kwargs):
        context = super(EnseignantEDTView, self).get_context_data(**kwargs)
        enseignant_ = get_object_or_404(Enseignant, id=self.kwargs.get('enseignant_pk'))
        context['enseignant'] = enseignant_
        return context


class EnseignantCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Enseignant
    fields = ['nom', 'prenom', 'eps', 'nom_a', 'prenom_a', 'eps_a', 'sexe', 'statut', 'tel', 'grade', 'charge_statut',
              'situation', 'bureau', 'bal', 'webpage', 'edt']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_enseignant'
    success_message = "L'enseignant a été ajouté avec succès!"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('enseignant_list')
        return form

    def get_context_data(self, **kwargs):
        context = super(EnseignantCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter un(e) enseignant(e)'
        return context


class EnseignantUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = Enseignant
    fields = ['nom', 'prenom', 'eps', 'nom_a', 'prenom_a', 'eps_a', 'sexe', 'statut', 'tel', 'grade', 'charge_statut',
              'situation', 'bureau', 'bal', 'webpage', 'edt']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_enseignant'
    success_message = "Le dossier de l'enseignant(e) a été modifié avec succès!"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('enseignant_list')
        return form


class EnseignantDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/import.html'

    def test_func(self):
        enseignant_ = get_object_or_404(Enseignant, id=self.kwargs.get("pk"))
        return self.request.user.is_staff_or_teacher_himself(enseignant_.id)

    def get_context_data(self, **kwargs):
        context = super(EnseignantDetailView, self).get_context_data(**kwargs)
        titre = 'Informations Enseignant'
        context['titre'] = titre
        enseignant_ = get_object_or_404(Enseignant, id=self.kwargs.get("pk"))
        context['form'] = EnseignantDetailForm(instance=enseignant_)

        return context


class PublicEtudiantListView(TemplateView):
    template_name = 'scolar/filter_list.html'

    def get_queryset(self, **kwargs):
        return Etudiant.objects.filter(public_profile=True).order_by('nom', 'prenom').annotate(
            rang_min=Min('inscriptions__rang'))

    def get_context_data(self, **kwargs):
        context = super(PublicEtudiantListView, self).get_context_data(**kwargs)
        filter_ = EtudiantFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()
        private = False
        if not self.request.user.is_authenticated:
            private = True
        else:
            private = not self.request.user.is_staff_only()
        exclude_ = []
        if private:
            exclude_.append('date_naissance')
            exclude_.append('tel')

        table = EtudiantTable(filter_.qs, exclude=exclude_)
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['back'] = reverse('home')
        if self.request.user.is_authenticated:
            if self.request.user.is_direction():
                btn_list = {}
                btn_list['Import Etudiants'] = reverse('etudiants_import')
                btn_list['Import Màj Etudiants'] = reverse('etudiants_import_maj')
                btn_list['Import Tutorats'] = reverse('tutorats_import')
                btn_list['Import Inscriptions'] = reverse('inscriptions_import')
                btn_list['Import Affectations Groupes'] = reverse('import_affectation_groupe')

                context['btn_list'] = btn_list
        else:
            messages.warning(self.request,
                             "N'apparaîtront ici que les étudiants ayant choisis de rendre leur profil public.")
            messages.info(self.request, "Pour consulter plus de profils, merci de vous connecter à votre compte.")
        context['titre'] = 'Liste des étudiants'
        return context


class EtudiantListView(LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin, PublicEtudiantListView):
    permission_required = 'scolar.view_etudiant'

    def test_func(self):
        return self.request.user.is_enseignant() or self.request.user.is_staff_only()

    def get_queryset(self, **kwargs):
        return Etudiant.objects.all().order_by('nom', 'prenom').annotate(rang_min=Min('inscriptions__rang'))


class EtudiantInscriptionListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'scolar/list.html'
    permission_required = 'scolar.view_inscription'

    def get_context_data(self, **kwargs):
        context = super(EtudiantInscriptionListView, self).get_context_data(**kwargs)
        etudiant_ = Etudiant.objects.get(matricule=self.kwargs.get('etudiant_pk'))
        parcours = InscriptionEtudiantTable(
            Inscription.objects.filter(etudiant=etudiant_).order_by('formation__annee_univ'),
            exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(parcours)
        context['table'] = parcours
        context['titre'] = 'Parcours de %s' % str(etudiant_)
        context['back'] = reverse('etudiant_list')
        if self.request.user.has_perm('scolar.add_inscription'):
            context['create_url'] = reverse('inscription_create', kwargs={'etudiant_pk': etudiant_.matricule})
            context['create_btn'] = 'Inscription'

        return context


@login_required
def groupe_list_export_view(request, groupe_pk, periode_pk):
    if request.user.is_etudiant():
        return redirect('/accounts/login/?next=%s' % request.path)

    try:
        # Create the HttpResponse object with the appropriate CSV header.
        groupe = get_object_or_404(Groupe, id=groupe_pk)
        periode = get_object_or_404(PeriodeProgramme, id=periode_pk)
        inscription_list = Inscription.objects.filter(inscription_periodes__groupe=groupe_pk,
                                                      inscription_periodes__periodepgm=periode_pk).order_by(
            'etudiant__nom', 'etudiant__prenom')
        header = ['Matricule', 'Email', 'Nom', 'Prenom', 'Situation', ]
        sheet = Dataset()
        sheet.headers = header

        for inscrit_ in inscription_list:
            row_ = []
            row_.append(inscrit_.etudiant.matricule)
            row_.append(inscrit_.etudiant.user.email)
            row_.append(inscrit_.etudiant.nom)
            row_.append(inscrit_.etudiant.prenom)
            row_.append(
                "Maladie" if inscrit_.decision_jury.startswith("M") else dict(DECISIONS_JURY)[inscrit_.decision_jury])
            sheet.append(row_)

        filename = str(groupe) + '_' + str(periode.periode.code) + '.xlsx'
        filename = filename.replace(' ', '_')

        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=' + filename + ";"
        response.write(sheet.xlsx)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: Il y a eu une erreur lors de l'export du fichier des étudiants. Merci de le signaler à l'administrateur.")
    return response


class EtudiantGroupeListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'scolar.view_inscription'
    template_name = 'scolar/list.html'

    def get_queryset(self, **kwargs):
        return Inscription.objects.filter(inscription_periodes__groupe=self.kwargs.get('groupe_pk'),
                                          inscription_periodes__periodepgm=self.kwargs.get('periode_pk')).order_by(
            'etudiant__nom', 'etudiant__prenom')

    def get_context_data(self, **kwargs):
        context = super(EtudiantGroupeListView, self).get_context_data(**kwargs)
        self.groupe_ = Groupe.objects.get(id=self.kwargs.get('groupe_pk'))
        table = InscriptionGroupeTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['table'] = table
        context['titre'] = 'Liste des étudiants du groupe ' + str(self.groupe_)
        # context['back'] = reverse('groupe_all_list')

        return context


def get_charge_context(enseignant_qs):
    context = {}
    enseignant_list = enseignant_qs
    charges = Charge.objects.filter(annee_univ__encours=True)
    periode_list = Periode.objects.all()
    charge_list = {}
    for enseignant_ in enseignant_list:
        charge_enseignement_semaine_periode = 0
        charge_totale_periode = 0
        for periode_ in periode_list:
            charge_enseignant = charges.filter(realisee_par=enseignant_, periode=periode_)
            charge_enseignant_activite = charge_enseignant.values('realisee_par', 'vh_eq_td', 'activite__module',
                                                                  'activite__type').annotate(
                nb_activites=Count('activite__type'))
            charge_enseignement_semaine = 0
            charge_detail = ''
            charge_tot = 0
            for charge_ in charge_enseignant_activite:
                if charge_['activite__module']:
                    module_ = get_object_or_404(Module, id=charge_['activite__module'])
                    charge_detail += str(charge_['nb_activites']) + 'x ' + str(charge_['activite__type']) + ' ' + str(
                        module_.matiere.code) + ' ' + str(charge_['vh_eq_td']) + 'h<br>'
            for charge_ in charge_enseignant:
                if charge_.repeter_chaque_semaine:
                    charge_tot += charge_.vh_eq_td * charge_.periode.nb_semaines
                else:
                    charge_tot += charge_.vh_eq_td
                if not charge_.activite:
                    charge_detail += dict(TYPE_CHARGE)[charge_.type] + ' ' + str(charge_.obs) + ' ' + str(
                        charge_.vh) + 'h <br>'
                if charge_.repeter_chaque_semaine:
                    charge_enseignement_semaine += charge_.vh_eq_td
            charge_enseignement_semaine_periode += charge_enseignement_semaine
            charge_totale_periode += charge_tot
            charge_list[str(enseignant_.id) + '_semaine_%s' % str(periode_.code)] = charge_enseignement_semaine
            charge_list[str(enseignant_.id) + '_detail_%s' % str(periode_.code)] = charge_detail
            charge_list[str(enseignant_.id) + '_tot_%s' % str(periode_.code)] = charge_tot
        charge_list[str(enseignant_.id) + '_moy_semaine'] = charge_enseignement_semaine_periode / periode_list.count()
        charge_list[str(enseignant_.id) + '_tot_an_prv'] = charge_totale_periode
        charge_list[str(enseignant_.id) + '_tot_statut'] = enseignant_.charge_statut
        charge_list[str(enseignant_.id) + '_tot_ratio'] = round(100, 2) if enseignant_.statut == 'V' else round(
            charge_totale_periode / enseignant_.charge_statut * 100, 2)
    context['periode_list'] = periode_list
    context['enseignant_list'] = enseignant_list
    context['charge_list'] = charge_list
    return context


@login_required
@permission_required('scolar.view_charge')
def charge_list_view(request):
    if not request.user.is_top_management():
        messages.error(request, "Vous n'avez pas les permissions pour accéder à cette vue.")
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ChargeFilterForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            form_data = form.cleaned_data
            enseignant_list = form_data['enseignant_list'] if form_data[
                'enseignant_list'] else Enseignant.objects.filter(situation='A').order_by('nom', 'prenom').values_list(
                'id')
            charge_inf = decimal.Decimal(form_data['charge_inf']) if form_data['charge_inf'] else 0
            charge_sup = decimal.Decimal(form_data['charge_sup']) if form_data['charge_sup'] else 1000

            enseignant_filter = []
            for enseignant in Enseignant.objects.filter(id__in=enseignant_list):
                if (enseignant.ratio_charge_annuelle_encours() <= charge_sup) and (
                        enseignant.ratio_charge_annuelle_encours() >= charge_inf):
                    enseignant_filter.append(enseignant.id)
            qs = Enseignant.objects.filter(id__in=enseignant_filter)

            messages.success(request, "Le filtre a été appliqué avec succès. Ci-après la liste des charges demandée.")
    else:

        form = ChargeFilterForm()
        qs = Enseignant.objects.filter(situation='A').order_by('nom', 'prenom')
        messages.info(request, "Utilisez ce formulaire pour filtrer les charges selon les critères ci-après.")
    try:
        context = get_charge_context(qs)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: lors de la création de la table des charges par enseignant. Merci de le signaler à l'administrateur.")
    context['form'] = form
    context['titre'] = "Liste des charges par enseignant"
    return render(request, 'scolar/charge_list.html', context)


class ChargeEnseignantView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = ('scolar.view_charge')
    template_name = 'scolar/charge_list.html'

    def get_context_data(self, **kwargs):
        context = super(ChargeEnseignantView, self).get_context_data(**kwargs)
        try:
            context.update(get_charge_context(Enseignant.objects.filter(id=self.request.user.enseignant.id)))
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération de la liste des charges. Merci de le signaler à l'administrateur.")
        context['titre'] = "Synthèse de la charge de M./Mme " + str(self.request.user.enseignant)
        return context


class ChargeEnseignantDetailView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UserPassesTestMixin,
                                 TemplateView):
    permission_required = 'scolar.view_charge'
    template_name = 'scolar/list.html'

    def test_func(self):
        return self.request.user.is_direction() or (
                    self.request.user.is_enseignant() and self.request.user.enseignant.id == int(
                self.kwargs.get('enseignant_pk')))

    def get_queryset(self, **kwargs):
        return Charge.objects.filter(annee_univ__encours=True, realisee_par=self.kwargs.get('enseignant_pk')).order_by(
            'periode__ordre')

    def get_context_data(self, **kwargs):
        context = super(ChargeEnseignantDetailView, self).get_context_data(**kwargs)
        try:
            enseignant_ = get_object_or_404(Enseignant, id=self.kwargs.get('enseignant_pk'))
            table = ChargeEnseignantTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
            RequestConfig(self.request).configure(table)
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request, "ERREUR: lors de la construction de la table des charges d'un enseignant!")
        context['titre'] = 'Charge détaillée de ' + str(enseignant_)
        context['table'] = table
        if self.request.user.has_perm('scolar.add_charge'):
            context['create_btn'] = "Charge"
            context['create_url'] = reverse('charge_enseignant_create',
                                            kwargs={'enseignant_pk': self.kwargs.get('enseignant_pk')})
            btn_list = {}
            btn_list['Ajout Charge Selon Modèle'] = reverse('charge_selon_config_create',
                                                            kwargs={'enseignant_pk': self.kwargs.get('enseignant_pk')})
            context['btn_list'] = btn_list
        context['back'] = reverse('charge_enseignant', kwargs={'enseignant_pk': self.kwargs.get('enseignant_pk')})
        return context


class ChargeEnseignantCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'scolar.add_charge'
    model = Charge
    fields = ['type', 'obs', 'vh', 'vh_eq_td', 'annee_univ', 'periode', 'realisee_par', 'cree_par',
              'repeter_chaque_semaine']
    template_name = 'scolar/create.html'
    success_message = "La charge a été rajoutée avec succès!"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        messages.info(self.request, "Utilisez ce formulaire pour renseigner une nouvelle charge!")
        messages.warning(self.request,
                         "Attention! Pour les activités d'enseignement, merci de passer par la Planification pour éviter toute incohérence!")
        form.fields['annee_univ'] = forms.ModelChoiceField(queryset=AnneeUniv.objects.filter(encours=True), initial=0,
                                                           required=True)
        form.fields['realisee_par'] = forms.ModelChoiceField(queryset=Enseignant.objects.all(),
                                                             initial=self.kwargs.get('enseignant_pk'), required=True)
        form.fields['cree_par'] = forms.ModelChoiceField(
            queryset=Enseignant.objects.filter(id=self.request.user.enseignant.id), initial=0, required=True)
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('charge_enseignant_detail',
                                   kwargs={'enseignant_pk': self.kwargs.get('enseignant_pk')})
        return form

    def get_context_data(self, **kwargs):
        context = super(ChargeEnseignantCreateView, self).get_context_data(**kwargs)
        titre = 'Créer une nouvelle charge'
        context['titre'] = titre
        return context


def charge_batch_create_view(request):
    if not request.user.is_top_management():
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportChargeForm(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            try:
                charge_file = request.FILES['file']
                dataset = Dataset()
                imported_data = dataset.load(charge_file.read().decode('utf-8'), format='csv')
                # la première ligne du fichier doit contenir des entêtes, au moins Nom, Prenom, Charge
                # insert imported_data in charge table
                form_data = form.cleaned_data
                annee_univ_ = form_data['annee_univ']
                periode_ = form_data['periode']
                type_ = form_data['type']
                obs_ = form_data['obs']
                repeter_chaque_semaine_ = form_data['repeter_chaque_semaine']
                for row in imported_data.dict:
                    try:
                        if row.get('Prenom'):
                            enseignant_ = get_enseignant_list_from_str(row['Nom'] + ' ' + row['Prenom'])[0]
                        else:
                            enseignant_ = get_enseignant_list_from_str(row['Nom'])[0]
                    except Exception:
                        messages.error(request, "L'enseignant " + row[
                            'Nom'] + " n'existe pas, veuillez corriger le nom ou l'insérer dans la base")
                        continue
                    vh_ = round(decimal.Decimal(row['Charge'].replace(',', '.')), 2)
                    Charge.objects.create(
                        annee_univ=annee_univ_,
                        periode=periode_,
                        type=type_,
                        obs=obs_,
                        repeter_chaque_semaine=repeter_chaque_semaine_,
                        realisee_par=enseignant_,
                        cree_par=request.user.enseignant,
                        vh=vh_,
                        vh_eq_td=vh_,
                    )
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: L'importation des charges s'est terminée avec des erreurs.")
                    messages.info(request, "Indiquer le fichier .csv des charges à créer")
                    messages.info(request,
                                  "La première ligne du fichier doit comporter au moins les colonnes suivantes: Nom, Prenom, Charge")
                    render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des Charges'})
            messages.success(request, "L'importation des charges a été réalisée avec succès!")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('charge_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportChargeForm()
        messages.info(request, "Indiquer le fichier .csv des charges à créer")
        messages.info(request,
                      "La première ligne du fichier doit comporter au moins les colonnes suivantes: Nom, Prenom, Charge")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des Charges'})


def charge_selon_config_create_view(request, enseignant_pk):
    if not request.user.is_top_management():
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SelectChargeConfigForm(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            try:
                form_data = form.cleaned_data
                charge_config_ = form_data['charge_config']

                Charge.objects.create(
                    annee_univ=get_object_or_404(AnneeUniv, encours=True),
                    periode=form_data['periode'],
                    type=charge_config_.categorie,
                    obs=form_data['obs'],
                    repeter_chaque_semaine=charge_config_.repeter_chaque_semaine,
                    realisee_par=get_object_or_404(Enseignant, id=enseignant_pk),
                    cree_par=request.user.enseignant,
                    vh=charge_config_.vh,
                    vh_eq_td=charge_config_.vh_eq_td,
                )
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: La création de charge selon modèle s'est terminée avec des erreurs. Merci de le signaler à l'administrateur")
                    messages.info(request,
                                  "Indiquez le type de charge et les informations compélementaires demandées dans ce formulaire.")
                    render(request, 'scolar/import.html', {'form': form, 'titre': 'Sélection charge selon modèle'})
            messages.success(request, "La création de charge a été réalisée avec succès!")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('charge_enseignant_detail', kwargs={'enseignant_pk': enseignant_pk}))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = SelectChargeConfigForm()
        messages.info(request,
                      "Indiquez le type de charge et les informations compélementaires demandées dans ce formulaire.")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Sélection charge selon modèle'})


class ActiviteChargeConfigListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/list.html'

    def test_func(self):
        return self.request.user.is_direction()

    def get_queryset(self, **kwargs):
        return ActiviteChargeConfig.objects.all().order_by('categorie', 'type')

    def get_context_data(self, **kwargs):
        context = super(ActiviteChargeConfigListView, self).get_context_data(**kwargs)

        table = ActiviteChargeConfigTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)

        context['table'] = table
        context['titre'] = 'Liste des configurations de charges liées à des activités pédagogiques'
        context['back'] = reverse('settings')
        if self.request.user.has_perm('scolar.add_activitechargeconfig'):
            context['create_url'] = reverse('activite_charge_config_create')
            context['create_btn'] = 'Ajouter une configuration'

        return context


class ActiviteChargeConfigCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = ActiviteChargeConfig
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_activitechargeconfig'
    success_message = "La configuration a été ajouté avec succès!"
    fields = ['categorie', 'type', 'titre', 'vh', 'vh_eq_td', 'repeter_chaque_semaine', 'repartir_entre_intervenants']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('settings')
        return form

    def get_context_data(self, **kwargs):
        context = super(ActiviteChargeConfigCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter une configuration'
        return context


class ActiviteChargeConfigUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = ActiviteChargeConfig
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_activitechargeconfig'
    success_message = "La configuration a été modifié avec succès!"
    fields = ['categorie', 'type', 'titre', 'vh', 'vh_eq_td', 'repeter_chaque_semaine', 'repartir_entre_intervenants']

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('settings')
        return form


class ActiviteChargeConfigDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'scolar.delete_activitechargeconfig'
    model = ActiviteChargeConfig
    template_name = 'scolar/delete.html'
    success_message = "La configuration a bien été supprimée."

    def get_success_url(self):
        return reverse('settings')


def tutorat_import_view(request):
    if not (request.user.is_direction()):
        messages.error(request, "Vous n'avez pas les permissions pour effectuer cette opération.")
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ImportFileForm(request.POST, request.FILES)
        # check whether it's valid:
        if form.is_valid():
            try:
                tutorat_file = request.FILES['file']
                dataset = Dataset()
                imported_data = dataset.load(tutorat_file.read().decode('utf-8'), format='csv')
                # la première ligne du fichier doit contenir des entêtes, au moins Matricule, Enseignant
                # update Etudiant with tuteur
                for row in imported_data.dict:
                    try:
                        etudiant_ = Etudiant.objects.get(matricule=row.get('Matricule'))
                        enseignant_ = get_enseignant_list_from_str(row.get('Enseignant'))[0]
                    except Exception:
                        messages.error(request, "L'étudiant" + row.get('Matricule') + " ou l'enseignant " + row[
                            'Enseignant'] + " n'existe pas, veuillez corriger le nom ou l'insérer dans la base")
                        continue
                    etudiant_.tuteur = enseignant_
                    etudiant_.save()
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: L'importation des tutorats s'est terminée avec des erreurs.")
                    messages.info(request, "Indiquer le fichier .csv des tutorat à créer")
                    messages.info(request,
                                  "La première ligne du fichier doit comporter au moins les colonnes suivantes: Matricule, Enseignant")
                    render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des Tutorats'})
            messages.success(request, "L'importation des tutorats a été réalisée avec succès!")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('etudiant_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = ImportFileForm()
        messages.info(request, "Indiquer le fichier .csv des tutorats à créer")
        messages.info(request,
                      "La première ligne du fichier doit comporter au moins les colonnes suivantes: Matricule, Enseignant")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Importer des Tutorats'})


class ChargeEnseignantUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'scolar.change_charge'
    model = Charge
    fields = ['type', 'obs', 'vh', 'vh_eq_td', 'annee_univ', 'periode', 'realisee_par', 'cree_par',
              'repeter_chaque_semaine']
    template_name = 'scolar/update.html'
    success_message = "La charge a été modifiée avec succès!"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        charge_ = get_object_or_404(Charge, id=self.kwargs.get('pk'))
        form.fields['annee_univ'] = forms.ModelChoiceField(queryset=AnneeUniv.objects.filter(encours=True), initial=0,
                                                           required=True)
        form.fields['cree_par'] = forms.ModelChoiceField(
            queryset=Enseignant.objects.filter(id=self.request.user.enseignant.id), initial=0, required=True)
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('charge_enseignant_detail', kwargs={'enseignant_pk': charge_.realisee_par.id})
        return form


class ChargeEnseignantDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'scolar.delete_charge'
    model = Charge
    template_name = 'scolar/delete.html'
    success_message = "La charge a bien été supprimée."

    def get_success_url(self):
        return reverse('charge_enseignant_detail', kwargs={'enseignant_pk': self.kwargs.get('enseignant_pk')})


class ActiviteCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'scolar.add_activite'
    model = Activite
    fields = ['type', 'module', 'cible', 'assuree_par', 'vh']
    template_name = 'scolar/create.html'
    success_message = "L'activité a été ajoutée avec succès!"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        try:
            groupe_ = get_object_or_404(Groupe, id=self.kwargs.get('groupe_pk'))
            module_ = get_object_or_404(Module, id=self.kwargs.get('module_pk'))
            formation_ = module_.formation
            form.helper = FormHelper()
            form.fields['module'] = forms.ModelChoiceField(queryset=Module.objects.filter(id=module_.id), initial=0)
            form.fields['cible'] = forms.ModelMultipleChoiceField(
                queryset=Groupe.objects.filter(section__formation__programme__ordre=formation_.programme.ordre,
                                               section__formation__annee_univ__encours=True),
                initial=Groupe.objects.filter(id=groupe_.id))

            form.fields['assuree_par'] = forms.ModelMultipleChoiceField(
                queryset=Enseignant.objects.all().order_by('nom'),
                widget=ModelSelect2MultipleWidget(
                    model=Enseignant,
                    search_fields=['nom__icontains', 'prenom__icontains'],
                ),
                help_text="Sélection multiple possible. Tapez le nom ou prénom de l'enseignant ou deux espaces pour avoir la liste complète.",

            )
            form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
            form.helper.add_input(
                Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
            self.success_url = reverse('planification_update',
                                       kwargs={'formation_pk': formation_.id, 'periode_pk': module_.periode.id})
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de l'ajout de l'activité. Merci de le signaler à l'administrateur.")
        return form

    def get_context_data(self, **kwargs):
        context = super(ActiviteCreateView, self).get_context_data(**kwargs)
        titre = 'Créer une nouvelle activité'
        context['titre'] = titre
        return context


class ActiviteUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'scolar.change_activite'
    model = Activite
    fields = ['type', 'module', 'cible', 'assuree_par', 'vh']
    template_name = 'scolar/update.html'
    success_message = "Activité modifiée avec succès!"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        activite_ = Activite.objects.get(id=self.kwargs.get('pk'))
        formation_ = Formation.objects.get(id=self.kwargs.get('formation_pk'))
        form.fields['module'] = forms.ModelChoiceField(
            queryset=Module.objects.filter(matiere__code=activite_.module.matiere.code,
                                           formation=activite_.module.formation), initial=activite_.module,
            disabled=False)
        form.fields['cible'] = forms.ModelMultipleChoiceField(
            queryset=Groupe.objects.filter(section__formation__programme__ordre=formation_.programme.ordre,
                                           section__formation__annee_univ__encours=True), initial=activite_.cible,
            disabled=False)
        form.fields['assuree_par'] = forms.ModelMultipleChoiceField(
            queryset=Enseignant.objects.all().order_by('nom'),
            widget=ModelSelect2MultipleWidget(
                model=Enseignant,
                search_fields=['nom__icontains', 'prenom__icontains'],
            ),
            help_text="Sélection multiple possible. Tapez le nom ou prénom de l'enseignant ou deux espaces pour avoir la liste complète.",

        )
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('planification_update', kwargs={'formation_pk': str(self.kwargs.get('formation_pk')),
                                                                   'periode_pk': str(self.kwargs.get('periode_pk'))})
        return form


class ActiviteDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'scolar.delete_activite'
    model = Activite
    template_name = 'scolar/delete.html'
    success_message = "L'activité a bien été supprimée."

    def get_success_url(self):
        return reverse('planification_update', kwargs={'formation_pk': str(self.kwargs.get('formation_pk')),
                                                       'periode_pk': str(self.kwargs.get('periode_pk'))})


class SpecialiteCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'scolar.add_specialite'
    model = Specialite
    fields = ['code', 'intitule', 'intitule_a', 'title']
    template_name = 'scolar/create.html'
    success_message = "La spécialité a été bien créée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_design')
        return form

    def get_context_data(self, **kwargs):
        context = super(SpecialiteCreateView, self).get_context_data(**kwargs)

        titre = 'Créer une Spécialité'
        context['titre'] = titre
        return context


class SpecialiteUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'scolar.change_specialite'
    model = Specialite
    fields = ['code', 'intitule', 'intitule_a', 'title']
    template_name = 'scolar/update.html'
    success_message = "La spécialité a été bien modifiée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        self.success_url = reverse('programme_design')
        return form

    def get_context_data(self, **kwargs):
        context = super(SpecialiteUpdateView, self).get_context_data(**kwargs)

        titre = 'Modifier la Spécialité'
        context['titre'] = titre
        return context


class PlanificationListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/filter_list.html'

    def test_func(self):
        return self.request.user.is_direction()

    def get_queryset(self, **kwargs):
        return Formation.objects.all().order_by('-annee_univ__annee_univ', 'programme__ordre')

    def get_context_data(self, **kwargs):
        context = super(PlanificationListView, self).get_context_data(**kwargs)

        filter_ = FormationFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()

        table = PlanificationTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)

        context['table'] = table
        context['filter'] = filter_
        context['titre'] = 'Liste des formations durant l\'année universitaire en cours'
        context['back'] = reverse('home')
        if self.request.user.has_perm('scolar.add_activite'):
            context['import_url'] = reverse('planning_import_from_fet')
            context['import_btn'] = 'Réinitialiser & Importer'

        return context


class PlanificationUpdateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/planification_update.html'

    def test_func(self):
        return self.request.user.is_direction()

    def get_context_data(self, **kwargs):
        context = super(PlanificationUpdateView, self).get_context_data(**kwargs)
        try:
            formation_ = get_object_or_404(Formation, id=self.kwargs.get('formation_pk'))
            periode_programme_ = get_object_or_404(PeriodeProgramme, id=self.kwargs.get('periode_pk'))
            module_list = Module.objects.filter(formation=formation_, periode=periode_programme_)
            groupe_list = Groupe.objects.filter(section__formation=formation_)
            activite_list = {}
            module_suivi_list = {}
            module_periode_list = []
            for groupe_ in groupe_list:
                for module_ in module_list:
                    module_suivi_ = ModulesSuivis.objects.filter(groupe=groupe_, module=module_)
                    key_ = str(groupe_.id) + '_' + str(module_.id)
                    if module_suivi_.exists():
                        module_suivi_ = module_suivi_.get()
                        if not module_suivi_.module in module_periode_list:
                            module_periode_list.append(module_suivi_.module)
                        module_suivi_list[key_] = module_suivi_
                        module_activite_list = Activite.objects.filter(module=module_, cible__in=[groupe_])
                        key_ = str(groupe_.id) + '_' + str(module_.id)
                        if module_activite_list.exists():
                            activite_list[key_] = module_activite_list
                    else:
                        module_suivi_list[key_] = None
                        if not module_ in module_periode_list:
                            module_periode_list.append(module_)
            context['module_periode_list'] = module_periode_list
            context['module_suivi_list'] = module_suivi_list
            context['groupe_list'] = groupe_list
            context['activite_list'] = activite_list
            context['formation'] = formation_
            context['periode'] = periode_programme_
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération du tableau de planification. Merci de le signaler à l'administrateur!")
        return context


@receiver(m2m_changed, sender=Activite.assuree_par.through)
def update_charge(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        for enseignant_ in instance.assuree_par.all():
            Charge.objects.update_or_create(activite=instance, realisee_par=enseignant_, defaults={
                'type': 'S' if instance.type.startswith("E_") else 'E',
                'activite': instance,
                'vh': instance.vh_par_enseignant(),
                'vh_eq_td': instance.vh_eq_td_par_enseignant(),
                'annee_univ': instance.module.formation.annee_univ,
                'periode': instance.module.periode.periode,
                'realisee_par': enseignant_,
                # 'cree_par':kwargs.get('request').GET.user.enseignant.id,
                'repeter_chaque_semaine': instance.repeter_chaque_semaine
            })
    elif action == "post_remove":
        Charge.objects.filter(activite=instance, realisee_par__in=pk_set).delete()
        Charge.objects.filter(activite=instance, realisee_par__in=instance.assuree_par.all()).update(
            vh=instance.vh_par_enseignant(),
            vh_eq_td=instance.vh_eq_td_par_enseignant(),
        )


@receiver(post_delete, sender=Activite)
def remove_charge(sender, instance, **kwargs):
    # supprimer les charges qui correspondent à l'activité supprimée
    Charge.objects.filter(activite=instance).delete()


class AbsenceEtudiantView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/list.html'

    def test_func(self):
        return self.request.user.is_staff_or_student_himself(self.kwargs.get('etudiant_pk'))

    def get_queryset(self, **kwargs):
        etudiant_pk_ = self.kwargs.get('etudiant_pk')
        module_pk_ = self.kwargs.get('module_pk')
        return AbsenceEtudiant.objects.filter(seance__activite__module__formation__annee_univ__encours=True,
                                              etudiant=etudiant_pk_, seance__activite__module=module_pk_)

    def get_context_data(self, **kwargs):
        context = super(AbsenceEtudiantView, self).get_context_data(**kwargs)
        table = AbsenceEtudiantTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['titre'] = 'Mes absences'
        context['table'] = table
        context['back'] = self.request.META.get('HTTP_REFERER')
        return context


class AbsenceEtudiantListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'scolar.view_absenceetudiant'
    template_name = 'scolar/filter_list.html'

    def get_queryset(self, **kwargs):
        return AbsenceEtudiant.objects.filter(seance__activite__module__formation__annee_univ__encours=True)

    def get_context_data(self, **kwargs):
        context = super(AbsenceEtudiantListView, self).get_context_data(**kwargs)
        filter_ = AbsenceEtudiantFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()
        table = AbsenceEtudiantTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['titre'] = 'Liste des absences'

        return context


class AbsenceEtudiantSeanceListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'scolar.view_absenceetudiant'
    template_name = 'scolar/list.html'

    def get_queryset(self, **kwargs):
        return AbsenceEtudiant.objects.filter(seance=self.kwargs.get('seance_pk'))

    def get_context_data(self, **kwargs):
        context = super(AbsenceEtudiantSeanceListView, self).get_context_data(**kwargs)
        table = AbsenceEtudiantTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['table'] = table
        context['titre'] = 'Liste des absences'
        context['back'] = reverse('assiduite', kwargs={'activite_pk': str(self.kwargs.get('activite_pk'))})

        return context


class AbsenceEtudiantUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = AbsenceEtudiant
    fields = ['etudiant', 'seance', 'justif', 'motif', 'date_justif']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_absenceetudiant'
    success_message = "L'absence de l'étudiant a bien été modifiée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['etudiant'] = forms.ModelChoiceField(queryset=Etudiant.objects.all(), disabled=True)
        form.fields['seance'] = forms.ModelChoiceField(queryset=Seance.objects.all(), disabled=True)
        form.fields['date_justif'] = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS,
                                                     widget=DatePickerInput(format='%d/%m/%Y'),
                                                     initial=datetime.date.today())
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('absence_list')
        return form


class AbsenceEtudiantDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'scolar.delete_absenceetudiant'
    model = AbsenceEtudiant
    template_name = 'scolar/delete.html'
    success_message = "L'absence a bien été supprimée."

    def get_success_url(self):
        if self.request.user.is_enseignant():
            return reverse('absence_seance_list', kwargs={'activite_pk': self.kwargs.get('activite_pk'),
                                                          'seance_pk': self.kwargs.get('seance_pk')})
        return reverse('absence_list')


class AbsenceEnseignantView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/list.html'

    def test_func(self):
        return self.request.user.is_staff_or_teacher_himself(self.kwargs.get('enseignant_pk'))

    def get_queryset(self, **kwargs):
        enseignant_pk_ = self.kwargs.get('enseignant_pk')
        module_pk_ = self.kwargs.get('module_pk')
        return AbsenceEnseignant.objects.filter(seance__activite__module__formation__annee_univ__encours=True,
                                                enseignant=enseignant_pk_, seance__activite__module=module_pk_)

    def get_context_data(self, **kwargs):
        context = super(AbsenceEnseignantView, self).get_context_data(**kwargs)
        table = AbsenceEnseignantTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['titre'] = 'Mes absences'
        context['table'] = table
        context['back'] = self.request.META.get('HTTP_REFERER')
        return context


class AbsenceEnseignantListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'scolar.view_absenceenseignant'
    template_name = 'scolar/filter_list.html'

    def get_queryset(self, **kwargs):
        return AbsenceEnseignant.objects.filter(seance__activite__module__formation__annee_univ__encours=True)

    def get_context_data(self, **kwargs):
        context = super(AbsenceEnseignantListView, self).get_context_data(**kwargs)
        filter_ = AbsenceEnseignantFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()
        table = AbsenceEnseignantTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['titre'] = 'Liste des absences d\'enseignants'
        return context


class AbsenceEnseignantUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = AbsenceEnseignant
    fields = ['enseignant', 'seance', 'justif', 'motif', 'seance_remplacement', 'date_justif']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_absenceenseignant'
    success_message = "L'absence de l'enseignant a bien été modifiée"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        absence_enseignant = AbsenceEnseignant.objects.get(id=self.kwargs.get('pk'))
        form.fields['enseignant'] = forms.ModelChoiceField(queryset=Enseignant.objects.all(), disabled=True)
        form.fields['seance'] = forms.ModelChoiceField(queryset=Seance.objects.all(), disabled=True)
        form.fields['seance_remplacement'] = forms.ModelChoiceField(
            queryset=Seance.objects.filter(activite=absence_enseignant.seance.activite).exclude(
                id=absence_enseignant.seance.id))
        form.fields['date_justif'] = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS,
                                                     widget=DatePickerInput(format='%d/%m/%Y'),
                                                     initial=datetime.date.today())
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('absence_enseignant_list')
        return form


class SeanceRattrapageCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Seance
    fields = ['activite', 'date', 'rattrapage']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_seance'
    success_message = "La séance de rattrapage a bien été créée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['activite'] = forms.ModelChoiceField(
            queryset=Activite.objects.filter(id=self.kwargs.get('activite_pk')), initial=0)
        form.fields['rattrapage'] = forms.BooleanField(initial=True)
        form.fields['date'] = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS,
                                              widget=DatePickerInput(format='%d/%m/%Y'), initial=datetime.date.today())
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('absence_enseignant_list')
        return form


@login_required
def signaler_absence_etudiant(request):
    if not (request.user.is_direction() or request.user.is_surveillance()):
        messages.error(request, "Vous n'avez pas accès à cette opération.")
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SeanceEtudiantSelectionForm(request.POST)

        # check whether it's valid:
        if form.is_valid():
            try:
                data = form.cleaned_data

                activite_ = data['activite']
                date_ = data['date']
                seance_, created = Seance.objects.get_or_create(activite=activite_, date=date_, defaults={
                    'activite': activite_,
                    'date': date_
                })
                absences_list = ''
                for inscription_ in data['inscription_absent_list']:
                    try:
                        resultat_ = Resultat.objects.get(inscription=inscription_,
                                                         module__matiere__code=activite_.module.matiere.code)
                    except Exception:
                        if settings.DEBUG:
                            raise Exception("Signaler Absence: Resultat inexitant ou Multiple")
                        else:
                            messages.error(request, str(
                                inscription_) + " Module inexistant ou multiple, merci de le signaler à l'administrateur")
                    else:
                        if not resultat_.acquis:
                            absence, created = AbsenceEtudiant.objects.get_or_create(seance=seance_,
                                                                                     etudiant=inscription_.etudiant,
                                                                                     defaults={
                                                                                         'seance': seance_,
                                                                                         'etudiant': inscription_.etudiant,
                                                                                     })
                            absences_list += str(inscription_) + ' : ' + settings.PROTOCOLE_HOST + reverse(
                                "etudiant_detail", kwargs={'pk': inscription_.etudiant.matricule}) + ' \n\n'
                        else:
                            messages.info(request, str(inscription_) + ' a déjà validé le module: ' + str(
                                activite_.module.matiere.code))

                # envoyer la liste des absents à la direction en cas d'examen
                if activite_.type.startswith('E_'):
                    email = EmailMessage('[Talents] Liste des Absences Signalées en ' + str(activite_),
                                         'Bonjour,\n' +
                                         'Ces absences en ' + str(activite_) + ' ont été enregistrées dans Talents\n' +
                                         absences_list +
                                         ' Un email leur a été transmis pour leur demander de justifier l\'absence dans les 48h.\n' +
                                         'Bien cordialement.\n' +
                                         'Département',
                                         to=[activite_.module.formation.programme.departement.responsable.user.email,
                                             activite_.module.coordinateur.user.email,
                                             request.user.email] +
                                            settings.STAFF_EMAILS['scolarite'] + settings.STAFF_EMAILS['direction'])

                    if settings.EMAIL_ENABLED:
                        email.send(fail_silently=True)

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: lors du signalement d'absence d'étudiants. Merci d'en informer l'administrateur")
                    return HttpResponseRedirect(reverse('absence_list'))
            # redirect to a new URL:
            messages.success(request, "Les absences ont bien été enregistrées.")
            return HttpResponseRedirect(reverse('absence_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = SeanceEtudiantSelectionForm()
        messages.info(request, "Merci de resenigner ce formulaire pour signaler la liste des absents.")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Signaler les absences d\'étudiants'})


@login_required
def absence_etudiant_report(request):
    if not request.user.is_staff_only():
        messages.error(request, "Vous n'avez pas accès à cette opération.")
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = AbsenceEtudiantReportSelectionForm(request.POST)

        # check whether it's valid:
        if form.is_valid():
            try:
                data = form.cleaned_data
                formation_ = data['formation']
                periode_ = data['periode']
                modules_suivis_list_ = ModulesSuivis.objects.filter(
                    groupe__section__formation=formation_,
                    module__periode__periode=periode_
                ).values('module__matiere__code').distinct()

                type_activite_list_ = data['type_activite_list']
                absence_justifiee_count = Count('justif', filter=Q(justif=True))
                absence_non_justifiee_count = Count('justif', filter=Q(justif=False))

                absence_etudiant_queryset = AbsenceEtudiant.objects.filter(
                    seance__activite__module__matiere__code__in=modules_suivis_list_,
                    seance__activite__type__in=type_activite_list_
                ).values(
                    'etudiant__matricule',
                    'etudiant__nom',
                    'etudiant__prenom',
                    'seance__activite__module__matiere__code',
                    'seance__activite__type'
                ).annotate(
                    absence_justifiee=absence_justifiee_count
                ).annotate(
                    absence_non_justifiee=absence_non_justifiee_count
                ).order_by('etudiant__nom', 'etudiant__prenom')

                absence_etudiant_report_list_ = {}
                for absence_etudiant_ in absence_etudiant_queryset:
                    matricule_ = absence_etudiant_['etudiant__matricule']
                    inscription_ = Inscription.objects.filter(formation=formation_, etudiant__matricule=matricule_,
                                                              decision_jury='C')
                    if inscription_.exists():
                        resultat_ = Resultat.objects.filter(
                            inscription__etudiant__matricule=absence_etudiant_['etudiant__matricule'],
                            module__matiere__code=absence_etudiant_['seance__activite__module__matiere__code'],
                            inscription__formation__annee_univ__encours=True,
                            acquis=False
                        )
                        if resultat_.exists():
                            resultat_ = resultat_.get()
                            if not matricule_ in absence_etudiant_report_list_.keys():
                                absence_etudiant_report_list_[matricule_] = {
                                    'nom': absence_etudiant_['etudiant__nom'],
                                    'prenom': absence_etudiant_['etudiant__prenom'],
                                }

                            if not resultat_.module.matiere.code in absence_etudiant_report_list_[matricule_].keys():
                                absence_etudiant_report_list_[matricule_][resultat_.module.matiere.code] = {}
                            type_activite_ = absence_etudiant_['seance__activite__type']
                            if not type_activite_ in absence_etudiant_report_list_[matricule_][
                                resultat_.module.matiere.code].keys():
                                absence_etudiant_report_list_[matricule_][resultat_.module.matiere.code][
                                    type_activite_] = {}
                            absence_etudiant_report_list_[matricule_][resultat_.module.matiere.code][type_activite_] = {
                                'absence_justifiee_count': absence_etudiant_['absence_justifiee'],
                                'absence_non_justifiee_count': absence_etudiant_['absence_non_justifiee']
                            }

                header = ['Matricule', 'Nom', 'Prenom', ]
                for module_suivi_ in modules_suivis_list_:
                    header.append(module_suivi_['module__matiere__code'])
                    # header.append('R('+module_suivi_['module__matiere__code']+')')
                sheet = Dataset()
                sheet.headers = header

                for matricule_, report_ in absence_etudiant_report_list_.items():
                    row_ = []
                    row_.append(matricule_)
                    row_.append(report_['nom'])
                    row_.append(report_['prenom'])
                    for module_suivi_ in modules_suivis_list_:
                        absence_justifiee_info_ = ''
                        absence_non_justifiee_info_ = ''
                        remplacement_ = False
                        if module_suivi_['module__matiere__code'] in report_.keys():
                            for type_activite_ in type_activite_list_:
                                nb_justifiees = report_[module_suivi_['module__matiere__code']][type_activite_][
                                    'absence_justifiee_count'] if type_activite_ in report_[
                                    module_suivi_['module__matiere__code']].keys() else 0
                                nb_non_justifiees = report_[module_suivi_['module__matiere__code']][type_activite_][
                                    'absence_non_justifiee_count'] if type_activite_ in report_[
                                    module_suivi_['module__matiere__code']].keys() else 0
                                if nb_justifiees > 0 and type_activite_.startswith('E_'):
                                    remplacement_ = True
                                if nb_justifiees > 0:
                                    if nb_justifiees == 1:
                                        absence_justifiee_info_ += ' ' + str(type_activite_)
                                    else:
                                        absence_justifiee_info_ += str(nb_justifiees) + ' x ' + str(type_activite_)
                                if nb_non_justifiees > 0:
                                    if nb_non_justifiees == 1:
                                        absence_non_justifiee_info_ += ' ' + str(type_activite_)
                                    else:
                                        absence_non_justifiee_info_ += str(nb_non_justifiees) + ' x ' + str(
                                            type_activite_)
                            if absence_justifiee_info_ != '':
                                absence_justifiee_info_ = 'OUI: ' + absence_justifiee_info_
                            if absence_non_justifiee_info_ != '':
                                absence_non_justifiee_info_ = 'NON: ' + absence_non_justifiee_info_

                        row_.append(absence_justifiee_info_ + '\n' + absence_non_justifiee_info_)
                    #                         if remplacement_:
                    #                             row_.append('1')
                    #                         else:
                    #                             row_.append('0')
                    sheet.append(row_)

                filename = 'Rapport_Absences_' + str(formation_) + '_' + str(periode_) + '.xlsx'
                filename = filename.replace(' ', '_')

                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=' + filename + ";"
                response.write(sheet.xlsx)

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: lors de la génération du rapport global des absences")
                    return HttpResponseRedirect(reverse('absence_list'))
            # redirect to a new URL:
            messages.success(request, "Le rapport global des absences a été généré correctement.")
            return response
            # if a GET (or any other method) we'll create a blank form
    else:
        form = AbsenceEtudiantReportSelectionForm()
        messages.info(request,
                      "Merci de resenigner ce formulaire pour sélectionner les activités à faire apparaître sur le rapport global des absences")
    return render(request, 'scolar/import.html',
                  {'form': form, 'titre': 'Sélection des activités du rapport des absences'})


@login_required
def signaler_absence_enseignant(request):
    if not (request.user.is_direction() or request.user.is_surveillance()):
        messages.error(request, "Vous n'avez pas accès à cette opération.")
        return redirect('/accounts/login/?next=%s' % request.path)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SeanceSelectionForm(request.POST)

        # check whether it's valid:
        if form.is_valid():
            try:
                enseignant_ = form.cleaned_data['enseignant']
                activite_ = form.cleaned_data['activite']
                date_ = form.cleaned_data['date']
                seance_, created = Seance.objects.get_or_create(activite=activite_, date=date_, defaults={
                    'activite': activite_,
                    'date': date_
                })
                absence, created = AbsenceEnseignant.objects.get_or_create(seance=seance_, enseignant=enseignant_,
                                                                           defaults={
                                                                               'seance': seance_,
                                                                               'enseignant': enseignant_,
                                                                           })
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: lors du signalement d'absence de l'enseignant. Merci d'en informer l'administrateur")
                    return HttpResponseRedirect(reverse('absence_enseignant_list'))
            # redirect to a new URL:
            messages.success(request, "L'absence a bien été enregistrée.")
            return HttpResponseRedirect(reverse('absence_enseignant_list'))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = SeanceSelectionForm()
        messages.info(request, "Merci d'indiquer le nom de l'enseignant absent, puis la séance et date de l'absence.")
    return render(request, 'scolar/import.html', {'form': form, 'titre': 'Signaler l\'absence d\'un enseignant'})


@receiver(post_save, sender=AbsenceEnseignant)
def email_absence_enseignant(sender, update_fields, instance, created, **kwargs):
    if created:
        nb_absences = instance.nb_absences()
        if nb_absences < 3:
            email = EmailMessage(str(nb_absences) + ' Absences Signalées en ' + str(instance.seance.activite),
                                 'Cher(e) collègue,\n' +
                                 'Nous espérons que vous allez bien!\n' +
                                 'Nous vous informons qu\'une absence au module ' + instance.seance.activite.module.matiere.code +
                                 ' a été signalée\n' +
                                 'Veuillez vous rapprocher du département afin de planifier la séance de remplacement si ce n\'est pas encore fait.\n' +
                                 'Bien cordialement.\n' +
                                 'Département', to=[instance.enseignant.user.email,
                                                    instance.seance.activite.module.formation.programme.departement.responsable.user.email] +
                                                   settings.STAFF_EMAILS['direction'])

        else:
            email = EmailMessage(str(nb_absences) + ' Absences Signalées en ' + str(instance.seance.activite),
                                 'Nom & Prénom: ' + instance.enseignant.nom + ' ' + instance.enseignant.prenom + '\n' +
                                 'Email: ' + instance.enseignant.user.email + '\n' +
                                 'Tel: ' + instance.enseignant.tel + '\n\n\n' +
                                 'Cher(e) collègue,\n' +
                                 'Nous espérons que vous allez bien!\n' +
                                 'Nous vous informons que ' + str(nb_absences) + ' absence au  ' + str(
                                     instance.seance.activite) +
                                 ' ont été signalée\n' +
                                 'Veuillez vous rapprocher du département afin de planifier la séance de remplacement si ce n\'est pas encore fait.\n' +
                                 'Par ailleurs, voudriez vous vous rapprocher de la direction des études afin de discuter de vos absences fréquentes et trouver ensemble les aménagements possibles afin de les éviter.\n' +
                                 'Bien cordialement.\n' +
                                 'Département', to=[instance.enseignant.user.email,
                                                    instance.seance.activite.module.formation.programme.departement.responsable.user.email] +
                                                   settings.STAFF_EMAILS['direction'])

        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)


def index(request):
    context = {}
    return render(request, 'scolar/index.html', context)


def home(request):
    context = {}
    return render(request, 'scolar/home.html', context)


class ActiviteEtudiantTableView(LoginRequiredMixin, TemplateView):
    template_name = 'scolar/modal_filter_list.html'

    def get_queryset(self, **kwargs):
        try:
            liste_inscription_encours = Inscription.objects.filter(etudiant=self.request.user.etudiant,
                                                                   formation__annee_univ__encours=True)
            liste_groupe_encours = []
            for inscription_encours in liste_inscription_encours:
                for inscription_periode in inscription_encours.inscription_periodes.all():
                    if inscription_periode.groupe:
                        if not inscription_periode.groupe in liste_groupe_encours:
                            liste_groupe_encours.append(inscription_periode.groupe)
                            section_encours = inscription_periode.groupe.section.groupes.all().filter(
                                code__isnull=True).get()
                            liste_groupe_encours.append(section_encours)
            return Activite.objects.filter(cible__in=liste_groupe_encours)
        except Exception:
            messages.error(self.request,
                           "ERREUR: nous ne trouvons pas d'inscription en cours valide. Si ce n'est pas le cas, merci de le signaler à l'administration des études..")
            return Activite.objects.none()

    def get_context_data(self, **kwargs):
        context = super(ActiviteEtudiantTableView, self).get_context_data(**kwargs)
        filter_ = ActiviteEtudiantFilter(self.request.GET, request=self.request, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()
        table = ActiviteEtudiantTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['titre'] = 'Mon activité pédagogique'
        try:
            matiere_list = []
            inscription_list = Inscription.objects.filter(etudiant=self.request.user.etudiant,
                                                          formation__annee_univ__encours=True)
            for resultat_ in Resultat.objects.filter(inscription__in=inscription_list):
                matiere_list.append(resultat_.module.matiere)
            context.update(get_competence_context(MatiereCompetenceElement.objects.filter(matiere__in=matiere_list)))
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération de la matrice de compétences. Merci de le signaler à l'administrateur")

        return context


class ActiviteTableView(LoginRequiredMixin, TemplateView):
    template_name = 'scolar/modal_filter_list.html'
    titre = 'Mes activités pédagogiques'

    def get_queryset(self, **kwargs):
        return Activite.objects.filter(assuree_par__in=[self.request.user.enseignant],
                                       module__matiere__pfe=False).order_by(
            '-module__formation__annee_univ__annee_univ')

    def get_context_data(self, **kwargs):
        context = super(ActiviteTableView, self).get_context_data(**kwargs)
        filter_ = ActiviteFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()
        table = ActiviteTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['titre'] = self.titre
        try:
            matiere_list = []
            activite_list = self.get_queryset()
            for activite_ in activite_list:
                matiere_list.append(activite_.module.matiere)
            context.update(get_competence_context(MatiereCompetenceElement.objects.filter(matiere__in=matiere_list)))
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération de la matrice de compétences. Merci de le signaler à l'administrateur")
        return context


class ActiviteSoutenancesView(ActiviteTableView):
    titre = 'Mes soutenances et encadrements'

    def get_queryset(self, **kwargs):
        return Activite.objects.filter(assuree_par__in=[self.request.user.enseignant],
                                       module__matiere__pfe=True).order_by('-module__formation__annee_univ__annee_univ')


def get_note_list_context(inscription_list, module_pk, groupe_pk):
    context = {}
    module_ = get_object_or_404(Module, id=module_pk)
    evaluation_list = Evaluation.objects.filter(module=module_)

    resultat_list = {}
    note_list = {}
    for inscrit_ in inscription_list:
        # le résultat d'un étudiant dans un module est déjà créé lors de son inscription à un groupe
        resultat_ = Resultat.objects.get(inscription=inscrit_, module__matiere=module_.matiere)
        resultat_list[inscrit_.etudiant.matricule] = resultat_
        for eval_ in evaluation_list:
            note_ = Note.objects.filter(resultat__inscription=inscrit_, evaluation=eval_)
            if note_.exists():
                note_ = note_.get()
                key_ = str(inscrit_) + ' ' + str(eval_)
                note_list[key_] = note_
    context['module'] = module_
    context['evaluation_list'] = evaluation_list
    context['groupe'] = get_object_or_404(Groupe, id=groupe_pk) if groupe_pk != None else None
    context['inscription_list'] = inscription_list
    context['resultat_list'] = resultat_list
    context['note_list'] = note_list
    return context


class NoteListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "scolar/note_list.html"

    def test_func(self):
        if self.request.user.is_scolarite() or self.request.user.is_direction() or self.request.user.is_stage():
            return True
        elif self.request.user.is_enseignant():
            module_ = ModulesSuivis.objects.get(groupe=self.kwargs.get('groupe_pk'),
                                                module__matiere=self.kwargs.get('matiere_pk')).module
            groupe_ = get_object_or_404(Groupe, id=self.kwargs.get('groupe_pk'))
            groupe_section = groupe_.section.groupes.all().filter(
                code__isnull=True).get()  # le groupe qui représente la section
            return assure_module_groupe(self.request.user.enseignant, module_, groupe_) or assure_module_groupe(
                self.request.user.enseignant, module_, groupe_section)
        else:
            return False

    def get_queryset(self, **kwargs):
        groupe_ = get_object_or_404(Groupe, id=self.kwargs.get('groupe_pk'))
        module_ = ModulesSuivis.objects.get(groupe=self.kwargs.get('groupe_pk'),
                                            module__matiere=self.kwargs.get('matiere_pk')).module
        return Inscription.objects.filter(inscription_periodes__groupe=groupe_,
                                          inscription_periodes__periodepgm__periode=module_.periode.periode).order_by(
            'etudiant__nom', 'etudiant__prenom')

    def get_context_data(self, **kwargs):
        context = super(NoteListView, self).get_context_data(**kwargs)
        try:
            module_ = ModulesSuivis.objects.get(groupe=self.kwargs.get('groupe_pk'),
                                                module__matiere=self.kwargs.get('matiere_pk')).module
            context.update(get_note_list_context(self.get_queryset(**kwargs), module_.id, self.kwargs.get('groupe_pk')))
            messages.info(self.request,
                          "Vous pouvez introduire les notes des étudiants en les saisissant en cliquant sur le bouton Modifier")
            if not module_.matiere.pfe:
                messages.warning(self.request,
                                 "Si vous préférez charger les notes à partir d'un fichier Excel, veillez à ce que le fichier ait exactement la structure du fichier téléchargeable ci-après.")
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération du tableau des notes. Merci de le signaler à l'administrateur.")
        return context


class NoteEtudiantListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "scolar/note_list.html"

    def test_func(self):
        return self.request.user.is_staff_or_student_himself(self.kwargs.get('etudiant_pk'))

    def get_context_data(self, **kwargs):
        context = super(NoteEtudiantListView, self).get_context_data(**kwargs)
        try:
            # module_=ModulesSuivis.objects.get(groupe__inscrits__etudiant__matricule__in=[self.kwargs.get('etudiant_pk')], groupe__section__formation__annee_univ__encours=True, module__matiere=self.kwargs.get('matiere_pk')).module
            module_ = Resultat.objects.get(inscription__etudiant__matricule=self.kwargs.get('etudiant_pk'),
                                           inscription__formation__annee_univ__encours=True,
                                           module__matiere=self.kwargs.get('matiere_pk')).module
            context.update(get_note_list_context(
                Inscription.objects.filter(etudiant=self.kwargs.get('etudiant_pk'), formation=module_.formation),
                module_.id,
                None))
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération du tableau des notes. Merci de le signaler à l'administrateur.")
        return context


class SeanceTableView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/list.html'

    def test_func(self):
        if self.request.user.is_scolarite() or self.request.user.is_surveillance():
            return True
        elif self.request.user.is_enseignant():
            activite_ = get_object_or_404(Activite, id=self.kwargs.get('activite_pk'))
            return assure_module(self.request.user.enseignant, activite_.module)
        else:
            return False

    def get_queryset(self, **kwargs):
        return Seance.objects.filter(activite__id=self.kwargs.get('activite_pk'))

    def get_context_data(self, **kwargs):
        context = super(SeanceTableView, self).get_context_data(**kwargs)
        table = SeanceTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['table'] = table
        context['back'] = reverse('activite')
        context['create_url'] = reverse('seance_create', kwargs={'activite_pk': self.kwargs.get('activite_pk')})
        context['create_btn'] = 'Séance'
        return context


class AnneeUnivListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'scolar/list.html'

    permission_required = 'scolar.view_anneeuniv'

    def get_context_data(self, **kwargs):
        context = super(AnneeUnivListView, self).get_context_data(**kwargs)
        table = AnneeUnivTable(AnneeUniv.objects.all().order_by('-annee_univ'),
                               exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['table'] = table
        context['back'] = self.request.META.get('HTTP_REFERER')
        if self.request.user.has_perm('scolar.add_anneeuniv'):
            context['create_url'] = reverse('anneeuniv_create')
            context['create_btn'] = 'Année'
        return context


class AnneeUnivUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = AnneeUniv
    fields = ['annee_univ', 'debut', 'fin', 'encours']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_anneeuniv'
    success_message = "La modification de l'année universitaire a bien été effectuée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['debut'] = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS,
                                               widget=DatePickerInput(format='%d/%m/%Y'))
        form.fields['fin'] = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS,
                                             widget=DatePickerInput(format='%d/%m/%Y'))
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('anneeuniv_list')
        return form


class AnneeUnivCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = AnneeUniv
    fields = ['annee_univ', 'debut', 'fin', 'encours']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_anneeuniv'
    success_message = "L'année universitaire a bien été rajoutée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['debut'] = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS,
                                               widget=DatePickerInput(format='%d/%m/%Y'))
        form.fields['fin'] = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS,
                                             widget=DatePickerInput(format='%d/%m/%Y'))
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('anneeuniv_list')
        return form

    def get_context_data(self, **kwargs):
        context = super(AnneeUnivCreateView, self).get_context_data(**kwargs)
        context['titre'] = "Ajouter une nouvelle année universitaire"
        return context


@receiver(post_save, sender=AnneeUniv)
def update_annee_univ_encours(sender, instance, created, **kwargs):
    # garder une seule année univ en cours
    if instance.encours:
        # mettre toutes les autres à False
        for annee_univ_ in AnneeUniv.objects.all():
            if (annee_univ_ != instance) and (annee_univ_.encours):
                annee_univ_.encours = False
                annee_univ_.save()


class FormationListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'scolar/list.html'
    permission_required = 'scolar.view_formation'

    def get_queryset(self, **kwargs):
        return Formation.objects.filter(annee_univ__annee_univ=kwargs.get('annee_univ_pk')).order_by('programme__ordre')

    def get_context_data(self, **kwargs):
        context = super(FormationListView, self).get_context_data(**kwargs)
        table = FormationTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['titre'] = 'Liste des formations durant l\'année universitaire %s' % self.kwargs.get('annee_univ_pk')
        context['table'] = table
        context['back'] = reverse('anneeuniv_list')
        if self.request.user.has_perm('scolar.add_formation'):
            context['create_url'] = reverse('formation_create',
                                            kwargs={'annee_univ_pk': self.kwargs.get('annee_univ_pk')})
            context['create_btn'] = 'Formation'
        return context


class FormationDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = Formation
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_formation'
    success_message = "La formation a bien été supprimée!"

    def get_success_url(self):
        return reverse('formation_list', kwargs={'annee_univ_pk': str(self.kwargs.get('annee_univ_pk'))})


def formation_archive_toggle_view(request, formation_pk):
    formation_ = Formation.objects.get(id=formation_pk)
    formation_.archive = not formation_.archive
    formation_.save(update_fields=['archive'])
    if formation_.archive:
        messages.success(request, 'La formation %s a été bien archivée' % str(formation_))
    else:
        messages.warning(request, 'La formation %s a été désarchivée' % str(formation_))
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class FormationCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Formation
    fields = ['programme', 'annee_univ', ]
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_formation'
    success_message = "La formation a bien été créée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['programme'] = forms.ModelChoiceField(queryset=Programme.objects.all().order_by('ordre'))
        form.fields['annee_univ'] = forms.ModelChoiceField(
            queryset=AnneeUniv.objects.filter(annee_univ=self.kwargs.get('annee_univ_pk')), initial=0)
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('formation_list', kwargs={'annee_univ_pk': str(self.kwargs.get('annee_univ_pk'))})

        return form

    def get_context_data(self, **kwargs):
        context = super(FormationCreateView, self).get_context_data(**kwargs)
        titre = 'Créer une Formation'
        context['titre'] = titre
        return context


class FormationUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = Formation
    fields = ['programme', 'annee_univ', ]
    template_name = 'scolar/update.html'
    permission_required = 'scolar.add_formation'
    success_message = "La formation a été bien mise à jour"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['programme'] = forms.ModelChoiceField(queryset=Programme.objects.all().order_by('ordre'))
        form.fields['annee_univ'] = forms.ModelChoiceField(
            queryset=AnneeUniv.objects.filter(annee_univ=self.kwargs.get('annee_univ_pk')), initial=0)
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('formation_list', kwargs={'annee_univ_pk': str(self.kwargs.get('annee_univ_pk'))})

        return form


@receiver(post_save, sender=Formation)
def add_modules_formation(sender, instance, created, **kwargs):
    if created:
        # créer les modules
        for periode_ in instance.programme.periodes.all():
            # on crée les sessions qui correspondent aux periodes du programme
            PeriodeFormation.objects.create(formation=instance, periode=periode_.periode,
                                            session=periode_.periode.session)
            for ue in periode_.ues.all():
                if ue.nature == 'OBL':
                    for matiere_ in ue.matieres.all():
                        Module.objects.create(formation=instance, matiere=matiere_, periode=periode_)


class SectionListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'scolar/list.html'
    permission_required = 'scolar.view_section'

    def get_queryset(self, **kwargs):
        return Section.objects.filter(formation__id=kwargs.get('formation_pk'))

    def get_context_data(self, **kwargs):
        context = super(SectionListView, self).get_context_data(**kwargs)
        table = SectionTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        formation_ = get_object_or_404(Formation, id=self.kwargs.get('formation_pk'))
        context['table'] = table
        context['titre'] = 'Liste des sections'
        context['back'] = reverse('formation_list', kwargs={'annee_univ_pk': formation_.annee_univ.annee_univ})
        if self.request.user.has_perm('scolar.add_section'):
            context['create_url'] = reverse('section_create', kwargs={'formation_pk': self.kwargs.get('formation_pk')})
            context['create_btn'] = 'Section'
        return context


class SectionDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = Section
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_section'
    success_message = "La section a bien été supprimée."

    def get_success_url(self):
        return reverse('section_list', kwargs={'formation_pk': str(self.kwargs.get('formation_pk'))})


class SectionCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Section
    fields = ['code', 'formation']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_section'
    success_message = "La section a bien été créée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['formation'] = forms.ModelChoiceField(
            queryset=Formation.objects.filter(id=self.kwargs.get('formation_pk')), initial=0)
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('section_list', kwargs={'formation_pk': str(self.kwargs.get('formation_pk'))})

        return form

    def get_context_data(self, **kwargs):
        context = super(SectionCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter une section'
        return context


@receiver(post_save, sender=Section)
def add_section_groupe(sender, instance, created, **kwargs):
    if created:
        grp = Groupe.objects.create(section=instance)


class GroupeListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'scolar/list.html'
    permission_required = 'scolar.view_groupe'

    def get_queryset(self, **kwargs):
        return Groupe.objects.filter(section__id=kwargs.get('section_pk'))

    def get_context_data(self, **kwargs):
        context = super(GroupeListView, self).get_context_data(**kwargs)
        table = GroupeTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        section_ = get_object_or_404(Section, id=self.kwargs.get('section_pk'))
        context['table'] = table
        context['titre'] = 'Liste des groupes'
        context['back'] = reverse('section_list', kwargs={'formation_pk': section_.formation.id})
        if self.request.user.has_perm('scolar.add_groupe'):
            context['create_url'] = reverse('groupe_create', kwargs={'section_pk': section_.id})
            context['create_btn'] = 'Groupe'
        return context


class GroupeAllListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/filter_list.html'

    def test_func(self):
        return self.request.user.is_staff_only() or self.request.user.is_enseignant()

    def get_queryset(self, **kwargs):
        return Groupe.objects.filter(section__formation__annee_univ__encours=True).order_by(
            'section__formation__programme__ordre', 'section__code', 'code')

    def get_context_data(self, **kwargs):
        context = super(GroupeAllListView, self).get_context_data(**kwargs)
        filter_ = GroupeAllFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()
        table = GroupeAllTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['titre'] = 'Liste des groupes'
        context['back'] = reverse('home')
        return context


class EnseignantGroupeAllListView(GroupeAllListView):

    def test_func(self):
        return self.request.user.is_enseignant()

    def get_queryset(self, **kwargs):
        mes_activites = Activite.objects.filter(assuree_par__in=[self.request.user.enseignant])
        mes_groupes = []
        for activite_ in mes_activites:
            for groupe_ in activite_.cible.all():
                if groupe_.code:
                    mes_groupes.append(groupe_.id)
                else:
                    section_ = groupe_.section
                    for groupe_ in section_.groupes.filter(code__isnull=False):
                        mes_groupes.append(groupe_.id)
        return Groupe.objects.filter(section__formation__annee_univ__encours=True, id__in=mes_groupes).order_by(
            'section__formation__programme__ordre', 'code')


class NotesFormationListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/filter_list.html'

    def test_func(self):
        return self.request.user.is_scolarite() or self.request.user.is_direction() or self.request.user.is_stage()

    def get_queryset(self, **kwargs):
        return Formation.objects.all().order_by('-annee_univ__annee_univ', 'programme__ordre')

    def get_context_data(self, **kwargs):
        context = super(NotesFormationListView, self).get_context_data(**kwargs)

        filter_ = FormationFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()

        table = NotesFormationTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table

        context['titre'] = 'Liste des formations et Notes par semestre'
        context['back'] = reverse('home')
        if self.request.user.is_direction():
            context['import_url'] = reverse('import_notes')
            context['import_btn'] = 'Importer des Notes'

        return context


class NotesFormationPFEListView(NotesFormationListView):
    def test_func(self):
        return self.request.user.is_stage()

    def get_queryset(self, **kwargs):
        return Formation.objects.filter(modules__matiere__pfe=True).order_by('-annee_univ__annee_univ',
                                                                             'programme__ordre')


class NotesFormationDetailView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/notes_formation_detail.html'

    def test_func(self):
        return self.request.user.is_scolarite() or self.request.user.is_stage() or self.request.user.is_direction()

    def get_modules_suivis_query_set(self):
        return ModulesSuivis.objects.filter(module__formation=self.kwargs.get('formation_pk'),
                                            module__periode=self.kwargs.get('periode_pk'))

    def get_context_data(self, **kwargs):
        context = super(NotesFormationDetailView, self).get_context_data(**kwargs)
        formation_ = get_object_or_404(Formation, id=self.kwargs.get('formation_pk'))
        periode_ = get_object_or_404(PeriodeProgramme, id=self.kwargs.get('periode_pk'))
        # on récupère les groues qui suivent des modules durant cette periode
        groupe_periode_list = InscriptionPeriode.objects.filter(periodepgm__periode=periode_.periode,
                                                                groupe__section__formation=self.kwargs.get(
                                                                    'formation_pk')).values('groupe')
        # groupe_list=Groupe.objects.filter(section__formation=self.kwargs.get('formation_pk'))
        groupe_list = Groupe.objects.filter(id__in=groupe_periode_list).order_by('code')
        module_suivi_list = self.get_modules_suivis_query_set()
        module_list = []  # on construit ici la liste des modules suivis sans doublants
        etat_saisie_list = {}
        for groupe_ in groupe_list:
            module_suivi_groupe = module_suivi_list.filter(groupe=groupe_)
            for module_suivi_ in module_suivi_groupe:
                if not module_suivi_.module in module_list:
                    module_list.append(module_suivi_.module)
                key = str(groupe_.id) + '_' + str(module_suivi_.module.id)
                etat_saisie_list[key] = module_suivi_.saisie_notes
        context['formation'] = formation_
        context['periode'] = periode_.periode
        context['groupe_list'] = groupe_list
        context['module_list'] = module_list
        context['etat_saisie_list'] = etat_saisie_list
        context['back'] = reverse('notes_formation_list')
        return context


class NotesFormationCoordinateurDetailView(NotesFormationDetailView):

    def test_func(self):
        return self.request.user.is_coordinateur(get_object_or_404(Module, id=self.kwargs.get('module_pk')))

    def get_modules_suivis_query_set(self):
        return ModulesSuivis.objects.filter(module=self.kwargs.get('module_pk'))

    def get_context_data(self, **kwargs):
        context = super(NotesFormationCoordinateurDetailView, self).get_context_data(**kwargs)
        context['back'] = reverse('coordination')
        return context


class EDTEtudiantView(TemplateView):
    template_name = 'scolar/edt_etudiant.html'

    def get_context_data(self, **kwargs):
        context = super(EDTEtudiantView, self).get_context_data(**kwargs)
        etudiant_ = self.request.user.etudiant
        inscription_list = Inscription.objects.filter(etudiant=etudiant_, formation__annee_univ__encours=True)
        edt_list = ''
        groupe_inscription_list = []
        for inscription_periode_ in InscriptionPeriode.objects.filter(inscription__in=inscription_list):
            if not inscription_periode_.groupe in groupe_inscription_list:
                groupe_inscription_list.append(inscription_periode_.groupe)
        for groupe_ in groupe_inscription_list:
            edt_list += '<br><br>' + groupe_.edt
        context['edt'] = edt_list
        context['etudiant'] = etudiant_
        return context


class TutoratListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'scolar/list.html'
    permission_required = 'scolar.view_module'

    def get_queryset(self, **kwargs):
        return Inscription.objects.filter(etudiant__tuteur=self.request.user.enseignant)

    def get_context_data(self, **kwargs):
        context = super(TutoratListView, self).get_context_data(**kwargs)
        table = TutoratTable(self.get_queryset(**kwargs), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)

        context['table'] = table
        context['titre'] = 'Mes tutorés'
        context['back'] = reverse('home')
        return context


class CoordinationModuleListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'scolar/filter_list.html'
    permission_required = ('scolar.view_module')

    def get_queryset(self, **kwargs):
        if self.request.user.is_direction() or self.request.user.is_scolarite():
            return Module.objects.filter(formation__annee_univ__encours=True).order_by('formation__programme__ordre',
                                                                                       'periode__periode__code',
                                                                                       'matiere__code')
        return Module.objects.filter(coordinateur=self.request.user.enseignant, formation__annee_univ__encours=True)

    def get_context_data(self, **kwargs):
        context = super(CoordinationModuleListView, self).get_context_data(**kwargs)
        filter_ = CoordinationModuleFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()

        table = ModuleTable(filter_.qs, exclude=exclude_columns(self.request.user) + ['notes'])
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['titre'] = 'Coordination des modules'
        context['back'] = reverse('home')
        return context


class CoordinationNotesModuleListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'scolar/filter_list.html'
    permission_required = ('scolar.view_module')

    def get_queryset(self, **kwargs):
        if self.request.user.is_direction():
            return Module.objects.filter(formation__annee_univ__encours=True).order_by('formation__programme__ordre',
                                                                                       'periode__periode__code',
                                                                                       'matiere__code')
        return Module.objects.filter(coordinateur=self.request.user.enseignant, formation__annee_univ__encours=True)

    def get_context_data(self, **kwargs):
        context = super(CoordinationNotesModuleListView, self).get_context_data(**kwargs)
        filter_ = CoordinationModuleFilter(self.request.GET, queryset=self.get_queryset(**kwargs))
        filter_.form.helper = FormHelper()

        table = ModuleTable(filter_.qs, exclude=exclude_columns(self.request.user) + ['coordonner'])
        RequestConfig(self.request).configure(table)
        context['filter'] = filter_
        context['table'] = table
        context['titre'] = 'Notes des groupes des modules dont j\'assure la coordination'
        context['back'] = reverse('home')
        return context


class ModuleDetailView(LoginRequiredMixin, DetailView):
    model = Module
    template_name_suffix = '_detail'

    def get_context_data(self, **kwargs):
        context = super(ModuleDetailView, self).get_context_data(**kwargs)
        module_ = context['object']
        evaluations = EvaluationTable(Evaluation.objects.filter(module=module_),
                                      exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(evaluations)
        context['evaluations'] = evaluations
        semainier = SemainierTable(Semainier.objects.filter(module=module_), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(semainier)
        context['semainier'] = semainier

        feedback_chart_ = FeedbackChart(module_pk=self.kwargs.get('pk'))
        question_list = Question.objects.all()
        context['feedback_chart'] = feedback_chart_
        context['question_list'] = question_list
        context['module'] = module_
        if self.request.user.is_enseignant():
            if assure_module(self.request.user.enseignant, module_):
                feedback_list = Feedback.objects.filter(module=module_, show=True)
                context['feedback_list'] = feedback_list
                # alerter l'enseignant si la somme des pondérations est # de 1
                if module_.somme_ponderation() != 1 and module_.somme_ponderation() != 0:
                    messages.error(self.request,
                                   "ATTENTION! La somme des pondérations des évaluations n'est pas égale à 1. Le coordinateur(trice) devrait corriger la formule")

        return context


class SemainierDeleteView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, DeleteView):
    model = Semainier
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_semainier'
    success_message = "La semaine a bien été supprimée."

    def test_func(self):
        module_ = Module.objects.get(id=self.kwargs.get('module_pk'))
        return module_.coordinateur == self.request.user.enseignant

    def get_success_url(self):
        return reverse("module_detail", kwargs={'pk': self.kwargs.get('module_pk')})


class SemainierUpdateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, UpdateView):
    model = Semainier
    fields = ['semaine', 'activite_cours', 'activite_dirigee', 'observation', 'objectifs', 'matiere_competence_element']
    template_name = 'scolar/update.html'
    success_message = "La semaine a bien été modifiée."

    def test_func(self):
        module_ = Module.objects.get(id=self.kwargs.get('module_pk'))
        return module_.coordinateur == self.request.user.enseignant

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        module_ = Module.objects.get(id=self.kwargs.get('module_pk'))
        form.fields['matiere_competence_element'] = forms.ModelChoiceField(
            queryset=MatiereCompetenceElement.objects.filter(matiere=module_.matiere), required=False)
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse("module_detail", kwargs={'pk': self.kwargs.get('module_pk')})

        return form


class SemainierCreateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, CreateView):
    model = Semainier
    fields = ['module', 'semaine', 'activite_cours', 'activite_dirigee', 'observation', 'objectifs',
              'matiere_competence_element']
    template_name = 'scolar/create.html'
    success_message = "La semaine a bien été créée."

    def test_func(self):
        module_ = Module.objects.get(id=self.kwargs.get('module_pk'))
        return module_.coordinateur == self.request.user.enseignant

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        module_ = Module.objects.get(id=self.kwargs.get('module_pk'))
        form.fields['module'] = forms.ModelChoiceField(queryset=Module.objects.filter(id=module_.id), initial=0)
        form.fields['matiere_competence_element'] = forms.ModelChoiceField(
            queryset=MatiereCompetenceElement.objects.filter(matiere=module_.matiere), required=False)
        form.helper.add_input(Submit('submit', 'Créer', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse("module_detail", kwargs={'pk': self.kwargs.get('module_pk')})

        return form

    def get_context_data(self, **kwargs):
        context = super(SemainierCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter une semaine'
        return context


class GroupeDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = Groupe
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_groupe'
    success_message = "Le groupe a bien été supprimé."

    def get_success_url(self):
        return reverse('groupe_list', kwargs={'section_pk': str(self.kwargs.get('section_pk'))})


class GroupeUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'scolar.change_groupe'
    model = Groupe
    fields = ['code', 'section', 'option', 'edt']
    template_name = 'scolar/update.html'
    success_message = "Le groupe a bien été modifié."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['section'] = forms.ModelChoiceField(
            queryset=Section.objects.filter(id=self.kwargs.get('section_pk')), initial=0)
        groupe_ = get_object_or_404(Groupe, id=self.kwargs.get('pk'))
        try:
            groupe_.pfe
            form.fields['code'] = forms.CharField(max_length=10, initial=groupe_.code)
        except ObjectDoesNotExist:
            form.fields['code'] = forms.ChoiceField(initial=groupe_.code, choices=CODES_GRP)
        section = get_object_or_404(Section, id=self.kwargs.get('section_pk'))
        form.fields['option'] = forms.ModelMultipleChoiceField(
            queryset=UE.objects.filter(periode__programme=section.formation.programme, nature='OPT'), required=False)
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('groupe_list', kwargs={'section_pk': str(self.kwargs.get('section_pk'))})

        return form


class GroupeCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'scolar.add_groupe'
    model = Groupe
    fields = ['code', 'section', 'option', 'edt']
    template_name = 'scolar/create.html'
    success_message = "Le groupe a bien été créé."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['code'] = forms.ChoiceField(choices=CODES_GRP)
        form.fields['section'] = forms.ModelChoiceField(
            queryset=Section.objects.filter(id=self.kwargs.get('section_pk')), initial=0)
        section = get_object_or_404(Section, id=self.kwargs.get('section_pk'))
        form.fields['option'] = forms.ModelMultipleChoiceField(
            queryset=UE.objects.filter(periode__programme=section.formation.programme, nature='OPT'), required=False)
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('groupe_list', kwargs={'section_pk': str(self.kwargs.get('section_pk'))})

        return form

    def get_context_data(self, **kwargs):
        context = super(GroupeCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter un groupe'
        return context


@receiver(post_save, sender=Groupe)
def add_modules_groupe(sender, instance, created, **kwargs):
    for periode_ in instance.section.formation.programme.periodes.all():
        for ue in periode_.ues.all():
            if ue.nature == 'OBL':
                for matiere_ in ue.matieres.all():
                    module_, created = Module.objects.get_or_create(matiere=matiere_,
                                                                    formation=instance.section.formation,
                                                                    periode=periode_, defaults={
                            'matiere': matiere_,
                            'formation': instance.section.formation,
                            'periode': ue.periode
                        })
                    module_suivi_, created = ModulesSuivis.objects.get_or_create(module=module_, groupe=instance,
                                                                                 defaults={
                                                                                     'module': module_,
                                                                                     'groupe': instance,
                                                                                 })


@receiver(m2m_changed, sender=Groupe.option.through)
def add_option_groupe(sender, instance, action, **kwargs):
    if action == "post_add":
        # créer les modules
        for ue in instance.option.all():
            for matiere_ in ue.matieres.all():
                module_, created = Module.objects.get_or_create(matiere=matiere_, formation=instance.section.formation,
                                                                periode=ue.periode, defaults={
                        'matiere': matiere_,
                        'formation': instance.section.formation,
                        'periode': ue.periode
                    })
                module_suivi_, created = ModulesSuivis.objects.get_or_create(module=module_, groupe=instance, defaults={
                    'module': module_,
                    'groupe': instance,
                })


class EvaluationCreateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, CreateView):
    model = Evaluation
    fields = ['type', 'ponderation', 'module']
    template_name = 'scolar/create.html'
    success_message = "L'évaluation a bien été créée."

    def test_func(self):
        module_ = get_object_or_404(Module, id=self.kwargs.get('module_pk'))

        # Si la formation est archivée ou si un PV est déjà établit alors ne pas autoriser la modification
        if module_.formation.archive or module_.pv_existe():
            messages.error(self.request,
                           "Il n'est plus possible de modifier les notes car un PV a été établit ou la saisie est clôturée.")
            return False

        if self.request.user.is_direction():
            return True
        elif self.request.user.is_enseignant():
            return self.request.user.enseignant == module_.coordinateur
        else:
            return False

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['module'] = forms.ModelChoiceField(queryset=Module.objects.filter(id=self.kwargs.get('module_pk')),
                                                       initial=0)
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('module_detail', kwargs={'pk': str(self.kwargs.get('module_pk'))})

        return form

    def get_context_data(self, **kwargs):
        context = super(EvaluationCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter une évaluation'
        return context


@login_required
def evaluation_competence_update_view(request, evaluation_pk):
    # if this is a POST request we need to process the form data
    eval_ = get_object_or_404(Evaluation, id=evaluation_pk)

    if request.user.is_enseignant():
        if request.user.enseignant != eval_.module.coordinateur:
            return redirect('/accounts/login/?next=%s' % request.path)
    elif not request.user.is_direction():
        return redirect('/accounts/login/?next=%s' % request.path)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = MatiereCompetenceForm(eval_.module.matiere.id, request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                form_data = form.cleaned_data
                competence_element_list = form_data['competence_element']
                for competence_element_ in competence_element_list:
                    EvaluationCompetenceElement.objects.get_or_create(evaluation=eval_,
                                                                      competence_element=competence_element_, defaults={
                            'evaluation': eval_,
                            'competence_element': get_object_or_404(CompetenceElement, id=competence_element_),
                            'commune_au_groupe': False,
                            'ponderation': 0
                        })
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: lors de l'ajout des éléments de compétence à l'évaluation. Merci de le signaler à l'administrateur.")
            messages.success(request, "Les éléments de compétence ont bien été rajoutés à l'évaluation.")
    else:
        form = MatiereCompetenceForm(eval_.module.matiere.id)
        messages.info(request, "Merci de sélectionner les éléments de compétence à rajouter à l'évaluation.")
    context = {}
    qs = EvaluationCompetenceElement.objects.filter(evaluation=eval_)
    table_ = EvaluationCompetenceElementTable(qs, exclude=exclude_columns(request.user))
    RequestConfig(request).configure(table_)
    context['table'] = table_
    context['form'] = form
    context['titre'] = 'Liste des éléments de compétence évalués'
    return render(request, 'scolar/form_list.html', context)


class EvaluationCompetenceElementUpdateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, UpdateView):
    model = EvaluationCompetenceElement
    fields = ['commune_au_groupe', 'ponderation', ]
    template_name = 'scolar/update.html'
    success_message = "L'élément de compétence a bien été modifié."

    def test_func(self):
        module_ = Evaluation.objects.get(id=self.kwargs.get('evaluation_pk')).module
        return self.request.user.is_coordinateur(module_)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('evaluation_competence_update',
                                   kwargs={'evaluation_pk': self.kwargs.get('evaluation_pk')})
        return form

    def get_context_data(self, **kwargs):
        context = super(EvaluationCompetenceElementUpdateView, self).get_context_data(**kwargs)
        context['titre'] = 'Modifier pondération de l\'élément de compétence dans l\'évaluation'
        return context


class EvaluationCompetenceElementDeleteView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, DeleteView):
    model = EvaluationCompetenceElement
    template_name = 'scolar/delete.html'
    success_message = "L'élément de compétence a bien été supprimé de l'évaluation."

    def test_func(self):
        module_ = Evaluation.objects.get(id=self.kwargs.get('evaluation_pk')).module
        return self.request.user.is_coordinateur(module_)

    def get_success_url(self):
        return reverse('evaluation_competence_update', kwargs={'evaluation_pk': self.kwargs.get('evaluation_pk')})


class EvaluationUpdateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, UpdateView):
    model = Evaluation
    fields = ['type', 'ponderation', 'module']
    template_name = 'scolar/update.html'
    success_message = "L'évaluation a bien été modifiée."

    def test_func(self):
        module_ = get_object_or_404(Module, id=self.kwargs.get('module_pk'))

        # Si la formation est archivée ou si un PV est déjà établit alors ne pas autoriser la modification
        if module_.formation.archive or module_.pv_existe():
            messages.error(self.request,
                           "Il n'est plus possible de modifier les notes car un PV a été établit ou la saisie est clôturée.")
            return False

        if self.request.user.is_direction():
            return True
        elif self.request.user.is_enseignant():
            return self.request.user.enseignant == module_.coordinateur
        else:
            return False

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['module'] = forms.ModelChoiceField(queryset=Module.objects.filter(id=self.kwargs.get('module_pk')),
                                                       initial=0, disabled=True)
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        form.helper.add_input(Button('modifier', 'Définir Compétences', css_class='btn-warning',
                                     onclick="window.location.href='" + reverse('evaluation_competence_update', kwargs={
                                         'evaluation_pk': self.kwargs.get('pk')}) + "'"))
        self.success_url = reverse('module_detail', kwargs={'pk': str(self.kwargs.get('module_pk'))})

        return form

    def get_context_data(self, **kwargs):
        context = super(EvaluationUpdateView, self).get_context_data(**kwargs)
        eval_ = context['object']
        context['titre'] = 'Modifier ' + str(eval_.type) + ' de ' + str(eval_.module.matiere.code)

        return context


class EvaluationDeleteView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, DeleteView):
    model = Evaluation
    template_name = 'scolar/delete.html'
    success_message = "L'évaluation a bien été supprimée."

    def test_func(self):
        module_ = get_object_or_404(Module, id=self.kwargs.get('module_pk'))

        # Si la formation est archivée ou si un PV est déjà établit alors ne pas autoriser la modification
        if module_.formation.archive or module_.pv_existe():
            messages.error(self.request,
                           "Il n'est plus possible de modifier les notes car un PV a été établit ou la saisie est clôturée.")
            return False

        if self.request.user.is_direction():
            return True
        elif self.request.user.is_enseignant():
            return self.request.user.enseignant == module_.coordinateur
        else:
            return False

    def get_success_url(self):
        return reverse('module_detail', kwargs={'pk': str(self.kwargs.get('module_pk'))})


class SeanceCreate(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Seance
    fields = ['date', 'activite', 'rattrapage']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_seance'
    success_message = "La séance a bien été créée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['date'] = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS,
                                              widget=DatePickerInput(format='%d/%m/%Y'))
        form.fields['activite'] = forms.ModelChoiceField(
            queryset=Activite.objects.filter(id=self.kwargs.get('activite_pk')), initial=0)
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('assiduite', kwargs={'activite_pk': str(self.kwargs.get('activite_pk'))})

        return form

    def get_context_data(self, **kwargs):
        context = super(SeanceCreate, self).get_context_data(**kwargs)
        context['titre'] = 'Création d\'une nouvelle séance'
        return context


class SeanceUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = Seance
    fields = ['date', 'activite', 'rattrapage']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_seance'
    success_message = "La séance a bien été modifiée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['date'] = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS,
                                              widget=DatePickerInput(format='%d/%m/%Y'))
        form.fields['activite'] = forms.ModelChoiceField(
            queryset=Activite.objects.filter(id=self.kwargs.get('activite_pk')), initial=0)
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('assiduite', kwargs={'activite_pk': str(self.kwargs.get('activite_pk'))})

        return form


class SeanceDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = Seance
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_seance'
    success_message = "La séance a bien été supprimée."

    def get_success_url(self):
        return reverse('assiduite', kwargs={'activite_pk': str(self.kwargs.get('activite_pk'))})


class ExamenListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/filter_list.html'

    def test_func(self):
        return self.request.user.is_direction()

    def get_context_data(self, **kwargs):
        context = super(ExamenListView, self).get_context_data(**kwargs)
        filter_ = ExamenFilter(self.request.GET, Seance.objects.filter(activite__type__startswith="E_").order_by(
            '-activite__module__formation__annee_univ__annee_univ', 'activite__module__formation__programme__ordre',
            'date', 'heure_debut'))
        filter_.form.helper = FormHelper()
        context['filter'] = filter_

        table = ExamenTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table)
        context['table'] = table
        context['btn_list'] = {
            'Créer Examen': reverse('examen_create'),
            'Envoi Convocations': reverse('envoi_convocations_examens'),
            'Affichage Répartition des Etudiants': reverse('affichage_convocations_examens')
        }
        context['titre'] = "Liste des examens"
        return context


# TODO Ajouter examen_update_view

@login_required
def examen_create_view(request):
    # if this is a POST request we need to process the form data

    if not (request.user.is_direction()):
        messages.error(request, "Vous n'êtes pas autorisés à accéder à cette fonction.")
        return redirect('/accounts/login/?next=%s' % request.path)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ExamenCreateForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                form_data = form.cleaned_data
                module_ = form_data['module']
                # Créer activite et seance correspondants à l'examen
                activite_ = Activite.objects.create(
                    module=module_,
                    type=form_data['type_activite'],
                    vh=form_data['duree'].hour + form_data['duree'].minute / 60,
                    repeter_chaque_semaine=False,
                )
                # rajouter les groupes concernés par l'examen
                for groupe_ in form_data['groupes']:
                    activite_.cible.add(groupe_)

                heure_fin_ = datetime.datetime(2020, 1, 1, 0, 0) + datetime.timedelta(
                    hours=form_data['heure_debut'].hour, minutes=form_data['heure_debut'].minute) + datetime.timedelta(
                    hours=form_data['duree'].hour, minutes=form_data['duree'].minute)  #
                heure_fin_ = heure_fin_.time()

                seance_, created = Seance.objects.update_or_create(activite=activite_, date=form_data['date'],
                                                                   defaults={
                                                                       'activite': activite_,
                                                                       'date': form_data['date'],
                                                                       'heure_debut': form_data['heure_debut'],
                                                                       'heure_fin': heure_fin_,
                                                                   })

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: lors de planification d'un examen.")
                    HttpResponseRedirect(reverse('examen_list'))
            messages.success(request, "L'examan a bien été planifié.")

            return HttpResponseRedirect(reverse('seance_salles_reservation', kwargs={'seance_pk': seance_.id}))
        else:
            context = {}
            context['form'] = form
            context['titre'] = "Planification d'un examen."
            return render(request, 'scolar/import.html', context)
    else:
        form = ExamenCreateForm()
        messages.info(request, "Merci de renseigner le formulaire pour planifier l'examen.")
        context = {}
        context['form'] = form
        context['titre'] = "Planification d'un examen."
        return render(request, 'scolar/import.html', context)


class ExamenDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'scolar.delete_activite'
    model = Activite
    template_name = 'scolar/delete.html'
    success_message = "L'examen a bien été supprimé."

    def get_success_url(self):
        return reverse('examen_list')


@login_required
def seance_salles_reservation(request, seance_pk):
    # if this is a POST request we need to process the form data
    seance_ = get_object_or_404(Seance, id=seance_pk)

    if not (request.user.is_direction()):
        messages.error(request, "Vous n'êtes pas autorisés à accéder à cette fonction.")
        return redirect('/accounts/login/?next=%s' % request.path)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SeanceSallesReservationForm(seance_pk, request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                form_data = form.cleaned_data
                # Ajouter les salles sélectionnées à la séance
                for salle_id_ in form_data['salles']:
                    salle_ = get_object_or_404(Salle, id=salle_id_)
                    seance_.salles.add(salle_)
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: lors de la réservation de salles.")
                    HttpResponseRedirect(reverse('examen_list'))
            messages.success(request, "Les salles ont bien été réservées.")

            return HttpResponseRedirect(reverse('placer_surveillants_etudiants', kwargs={'seance_pk': seance_.id}))
    else:
        form = SeanceSallesReservationForm(seance_pk)
        messages.info(request, "Merci de renseigner le formulaire pour réserver les salles.")
        context = {}
        context['salles'] = Salle.objects.all()
        context['form'] = form
        context['titre'] = "Réservtaion de salles."
        return render(request, 'scolar/seance_salles_reservation.html', context)


@login_required
def placer_surveillants_etudiants(request, seance_pk):
    # if this is a POST request we need to process the form data
    seance_ = get_object_or_404(Seance, id=seance_pk)

    if not (request.user.is_direction()):
        messages.error(request, "Vous n'êtes pas autorisés à accéder à cette fonction.")
        return redirect('/accounts/login/?next=%s' % request.path)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SurveillanceUpdateForm(seance_pk, request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                form_data = form.cleaned_data
                # Ajouter les surveillance, ajouter les enseignants à activite.assuree_par --> charges
                for enseignant_ in seance_.activite.assuree_par.all():
                    seance_.activite.assuree_par.remove(enseignant_)

                for salle_ in seance_.salles.all():
                    for surveillant_id_ in form_data[salle_.code]:
                        # rajouter le surveillant à activite.assuree_par
                        enseignant_ = get_object_or_404(Enseignant, id=surveillant_id_)
                        seance_.activite.assuree_par.add(enseignant_)

                        SurveillanceEnseignant.objects.update_or_create(seance=seance_, enseignant=enseignant_,
                                                                        defaults={
                                                                            'seance': seance_,
                                                                            'enseignant': enseignant_,
                                                                            'salle': salle_
                                                                        })
                # lancer la réservation des places aléatoires en tâche de fond
                t = threading.Thread(target=task_reservation_places_etudiants, args=[seance_, request.user])
                t.setDaemon(True)
                t.start()


            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: lors du placement des surveillants et étduiants en salles.")
                    return HttpResponseRedirect(reverse('examen_list'))
            messages.success(request,
                             "Les surveillants ont bien été affectées aux salles. Le placement des étudiants a été lancé. Une notification vous sera transmise une fois terminé.")

            return HttpResponseRedirect(reverse('examen_list'))
    else:
        form = SurveillanceUpdateForm(seance_pk)
        messages.info(request, "Merci de renseigner le formulaire pour affecter des surveillants aux salles.")
        context = {}
        context['form'] = form
        context['titre'] = "Affectation de surveillants."
        return render(request, 'scolar/import.html', context)


@transaction.atomic
def task_reservation_places_etudiants(seance_, user):
    try:

        # collecter toute les places disponible dans une liste
        place_disponible_list = []
        for salle_ in seance_.salles.all():
            for place_ in range(1, salle_.capacite() + 1):
                place_disponible_list.append((salle_, place_))
        # trier la liste des places d'une façon aléatoire
        random.shuffle(place_disponible_list)

        # affecter une place pour chaque étudiant concerné par la séance et retirer sa place des places disponibles
        for groupe_ in seance_.activite.cible.all():
            for inscription_ in groupe_.inscrits.all():
                # retirer une place de la liste
                try:
                    salle_, place_ = place_disponible_list.pop()
                except Exception:
                    raise Exception("ERREUR: Nombre de places insuffisant")
                place_, created = ReservationPlaceEtudiant.objects.update_or_create(seance=seance_,
                                                                                    inscription=inscription_, defaults={
                        'seance': seance_,
                        'inscription': inscription_,
                        'salle': salle_,
                        'place': place_,
                    })
                print(place_.inscription, ' ==> ', place_.salle, '(', place_.place, ')')
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage('[Talents] Erreur Réservation Places Etudiants ' + str(seance_),
                                 'Bonjour ' + str(user.enseignant.prenom) + ',\n' +
                                 'Une erreur s\'est produite lors de la réservation des places aux étudiants\n' +
                                 'Merci de vérifier les capacités des salles\n'
                                 'Bien cordialement.\n' +
                                 'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)
            else:
                print("ERREUR: Reservation Places Etudiants")
    email = EmailMessage('[Talents] Réservation Places Etudiants ' + str(seance_),
                         'Bonjour ' + str(user.enseignant.prenom) + ',\n' +
                         'La réservation des places aux étudiants pour passer :' + str(
                             seance_) + ' est effectuée avec succès' + '\n' +
                         'Vous pouvez imprimer le PV de l\'épreuve ici:\n' +
                         settings.PROTOCOLE_HOST + reverse('pv_examen_list', kwargs={'seance_pk': seance_.id}) + '\n' +
                         'Bien cordialement.\n' +
                         'Département', to=[user.email])
    if settings.EMAIL_ENABLED:
        email.send(fail_silently=True)
    else:
        print("Reservation Places Etudiants avec Succès!")


class PVExamenListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/pv_examen_list.html'

    def test_func(self):
        return self.request.user.is_direction() or self.request.user.is_scolarite() or self.request.user.is_surveillance()

    def get_context_data(self, **kwargs):
        context = super(PVExamenListView, self).get_context_data(**kwargs)
        seance_ = get_object_or_404(Seance, id=self.kwargs.get("seance_pk"))
        pv_list = {}
        for salle_ in seance_.salles.all():
            # construire la liste des places réservées dans la salle
            pv_list[salle_] = {
                'reservation_place_list': ReservationPlaceEtudiant.objects.filter(seance=seance_,
                                                                                  salle=salle_).order_by('place'),
                'surveillance_enseignant_list': SurveillanceEnseignant.objects.filter(seance=seance_,
                                                                                      salle=salle_).order_by(
                    'enseignant__nom')
            }
        context['pv_list'] = pv_list
        context['seance'] = seance_
        return context


# TODO écrire la vue pour l'envoie des convocation aux examens
# prévoir un formulaire pour récupérer l'intervalle des dates d'examens
# on convoque les étudiants, parcourir ReservationPlaceSalle dans les dates du formulaire et pour chaque étudiant envoyer un seul mail avec les réservations de places
# ajouter l'examen à l'agenda de l'étudiant
# on convoque les surveillants on parcours SurveillanceEnseignant dans l'intervalle des dates issues du formulaire
# on envoie un seul mail pour toutes les surveillances de l'enseignant
# planifier l'envoie d'un SMS de rappel le jour de la surveillance à 7h
# ajouter les surveillances à lagenda de l'enseignant
# Réserver les salles dans l'agenda
@login_required
def envoi_convocations_examens_view(request):
    # if this is a POST request we need to process the form data

    if not (request.user.is_direction()):
        messages.error(request, "Vous n'êtes pas autorisés à accéder à cette fonction.")
        return redirect('/accounts/login/?next=%s' % request.path)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = ExamenSelectForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                form_data = form.cleaned_data
                # Sélectionner les examens des formations compris dans l'intervalle des dates indiquées
                examen_list = Seance.objects.filter(activite__type__in=form_data['activite_type_list'],
                                                    activite__module__formation__in=form_data['formation_list'],
                                                    date__gte=form_data['date_debut'],
                                                    date__lte=form_data['date_fin']
                                                    ).order_by('date', 'heure_debut')
                # lancer l'envoi des convocations en tâche de fond
                t = threading.Thread(target=task_envoi_convocations_examens, args=[examen_list, request.user])
                t.setDaemon(True)
                t.start()
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: lors du lancement de l'envoi des convocations.")
                    return HttpResponseRedirect(reverse('examen_list'))
            messages.success(request,
                             "L'envoi des convocations a été lancé. Une notification vous sera transmise une fois la tâche terminée.")

            return HttpResponseRedirect(reverse('examen_list'))
    else:
        form = ExamenSelectForm()
        messages.info(request, "Merci de renseigner le formulaire pour sélectionner les examens à publier.")
        context = {}
        context['form'] = form
        context['titre'] = "Sélection des examens à publier"
        return render(request, 'scolar/import.html', context)


@transaction.atomic
def task_envoi_convocations_examens(examen_list, user):
    try:
        email_list = ()
        non_envoye = ''
        # convoquer les surveillants
        for enseignant_ in Enseignant.objects.filter(situation='A'):
            # sélectionner les surveillances programmées pour cet enseignant
            surveillance_list = SurveillanceEnseignant.objects.filter(
                seance__in=examen_list.values('id'),
                enseignant=enseignant_
            ).order_by('seance__date', 'seance__heure_debut')
            if surveillance_list.exists():
                # convoquer l'enseignant
                try:
                    enseignant_surveillance_list = ''
                    for surveillance_ in surveillance_list:
                        enseignant_surveillance_list += surveillance_.seance.date.strftime(
                            '%d/%m/%Y') + ' de ' + surveillance_.seance.heure_debut.strftime(
                            '%H:%M') + ' à ' + surveillance_.seance.heure_fin.strftime(
                            '%H:%M') + ' à la salle : ' + surveillance_.salle.code + '(' + dict(TYPES_ACT)[
                                                            surveillance_.seance.activite.type] + ' ' + surveillance_.seance.activite.module.matiere.code + ')\n'
                    recipient_ = [enseignant_.user.email, user.email]
                    email = ('[Talents] Convocation à Surveillance d\'Examens',
                             'Bonjour ' + str(enseignant_) + ',\n' +
                             'Nous vous prions d\'assurer la surveillance des examens suivants:\n' +
                             enseignant_surveillance_list +
                             'Bien cordialement.\n' +
                             'Département',
                             'talents@esi.dz',
                             recipient_)
                    email_list += (email,)
                except Exception:
                    non_envoye += str(enseignant_) + '\n'
                    continue

        # convoquer les étudiants
        inscription_examen_list = {}
        reservation_place_etudiant_list = ReservationPlaceEtudiant.objects.filter(
            seance__in=examen_list,
        ).order_by('seance__date', 'seance__heure_debut')
        for reservation_ in reservation_place_etudiant_list:
            if not reservation_.inscription in inscription_examen_list.keys():
                inscription_examen_list[reservation_.inscription] = ''
            inscription_examen_list[reservation_.inscription] += reservation_.seance.date.strftime(
                "%d/%m/%Y") + ' de ' + reservation_.seance.heure_debut.strftime(
                "%H:%M") + ' à ' + reservation_.seance.heure_fin.strftime(
                "%H:%M") + ' ==> ' + reservation_.salle.code + ':' + str(
                reservation_.place) + '(' + reservation_.seance.activite.module.matiere.code + ')\n'

        for inscription_, examen_list_ in inscription_examen_list.items():
            try:
                recipient_ = [inscription_.etudiant.user.email]
                email = ('[Talents] Convocation à Passer des Epreuves Ecrites',
                         'Bonjour ' + str(inscription_.etudiant.prenom) + ',\n' +
                         'Vous êtes convoqués à passer les épreuve écrites suivantes:\n' +
                         examen_list_ +
                         'Bien cordialement.\n' +
                         'Département',
                         'talents@esi.dz',
                         recipient_)
                email_list += (email,)
            except Exception:
                non_envoye += str(inscription_) + '\n'
                continue

        if settings.EMAIL_ENABLED:
            send_mass_mail(email_list, fail_silently=False)
        else:
            print(email_list)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage('[Talents] Erreur Envoi de Convocations',
                                 'Bonjour ' + str(user.enseignant.prenom) + ',\n' +
                                 'Une erreur s\'est produite lors de l\'envoi des convocations.\n' +
                                 'Bien cordialement.\n' +
                                 'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)
    else:
        email = EmailMessage('[Talents] Envoi des convocations pour examens',
                             'Bonjour ' + str(user.enseignant.prenom) + ',\n' +
                             'L\'envoi des convocations a été effectué avec succès' + '\n' +
                             'Bien cordialement.\n' +
                             'Département', to=[user.email])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)


@login_required
def affichage_convocations_examens_view(request):
    # if this is a POST request we need to process the form data

    if not (request.user.is_direction() or request.user.is_scolarite()):
        messages.error(request, "Vous n'êtes pas autorisés à accéder à cette fonction.")
        return redirect('/accounts/login/?next=%s' % request.path)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = AffichageExamenSelectForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                form_data = form.cleaned_data
                # Sélectionner les examens des formations compris dans l'intervalle des dates indiquées
                examen_list = Seance.objects.filter(activite__type__in=form_data['activite_type_list'],
                                                    activite__module__formation=form_data['formation'],
                                                    date__gte=form_data['date_debut'],
                                                    date__lte=form_data['date_fin']
                                                    ).order_by('date', 'heure_debut')
                # afficher les convocations des étudiants
                inscription_examen_list = {}
                reservation_place_etudiant_list = ReservationPlaceEtudiant.objects.filter(
                    seance__in=examen_list,
                ).order_by('inscription__etudiant__nom', 'inscription__etudiant__prenom', 'seance__date',
                           'seance__heure_debut')
                for reservation_ in reservation_place_etudiant_list:
                    if not reservation_.inscription in inscription_examen_list.keys():
                        inscription_examen_list[reservation_.inscription] = {}
                    inscription_examen_list[reservation_.inscription][
                        reservation_.seance.activite.module.matiere.code] = reservation_

                context = {}
                context['formation'] = form_data['formation']
                context['date_debut'] = form_data['date_debut']
                context['date_fin'] = form_data['date_fin']
                context['examen_list'] = examen_list
                context['inscription_examen_list'] = inscription_examen_list
                return render(request, 'scolar/affichage_convocations_examens.html', context)

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request, "ERREUR: lors de la génération de l'affichage des convocations.")
                    return HttpResponseRedirect(reverse('examen_list'))
    else:
        form = AffichageExamenSelectForm()
        messages.info(request, "Merci de renseigner le formulaire pour sélectionner les examens à publier.")
        context = {}
        context['form'] = form
        context['titre'] = "Sélection des examens à publier"
        return render(request, 'scolar/import.html', context)


class RepartitionCreditChart(Chart):
    chart_type = 'pie'

    def __init__(self, qs, *args, **kwargs):
        super(RepartitionCreditChart, self).__init__(*args, **kwargs)
        self.data = []
        self.labels = []
        self.colors = []
        try:
            ddc_data = Matiere.objects.filter(id__in=qs).values('ddc__intitule').annotate(
                somme_credits=Sum(F('credit')))
            total_data = Matiere.objects.filter(id__in=qs).aggregate(total=Sum(F('credit')))

            for ddc_ in ddc_data:
                self.labels.append(ddc_['ddc__intitule'])
                self.data.append(round(ddc_['somme_credits'] / total_data['total'], 2))
                self.colors.append("#%06x" % random.randint(0, 0xFFFFFF))
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la génération du graphique sur la répartition des crédits. Merci de le signaler à l'administrateur")

    def get_labels(self, *args, **kwargs):
        return self.labels

    def get_datasets(self, **kwargs):
        return [DataSet(data=self.data, backgroundColor=self.colors)]


class ProgrammeDesignView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/programme_design.html'

    def test_func(self):
        return self.request.user.is_direction()

    def get_context_data(self, **kwargs):
        context = super(ProgrammeDesignView, self).get_context_data(**kwargs)
        table_programme = ProgrammeTable(Programme.objects.all().order_by('ordre'),
                                         exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table_programme)
        context['table_programme'] = table_programme
        table_specialite = SpecialiteTable(Specialite.objects.all(), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table_specialite)
        context['table_specialite'] = table_specialite
        table_periode = PeriodeTable(Periode.objects.all(), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table_periode)
        context['table_periode'] = table_periode
        filter_ = MatiereFilter(self.request.GET, Matiere.objects.all().distinct().order_by('code'))
        filter_.form.helper = FormHelper()
        context['filter_matiere'] = filter_
        table_matiere = MatiereTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request, paginate={"per_page": 30}).configure(table_matiere)
        context['table_matiere'] = table_matiere
        context['repartition_credits_chart'] = RepartitionCreditChart(filter_.qs)
        table_diplome = DiplomeTable(Diplome.objects.all(), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table_diplome)
        context['table_diplome'] = table_diplome
        table_departement = DepartementTable(Departement.objects.all(), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table_departement)
        context['table_departement'] = table_departement
        return context


class ProgrammeListView(TemplateView):
    template_name = 'scolar/programme_list.html'

    def get_context_data(self, **kwargs):
        context = super(ProgrammeListView, self).get_context_data(**kwargs)
        table_programme = ProgrammeTable(Programme.objects.all().order_by('ordre'),
                                         exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table_programme)
        context['table_programme'] = table_programme
        table_specialite = SpecialiteTable(Specialite.objects.all(), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table_specialite)
        context['table_specialite'] = table_specialite
        filter_ = MatiereFilter(self.request.GET, Matiere.objects.all().order_by('code'))
        filter_.form.helper = FormHelper()

        table_matiere = MatiereTable(filter_.qs, exclude=exclude_columns(self.request.user))
        RequestConfig(self.request, paginate={"per_page": 30}).configure(table_matiere)
        context['filter_matiere'] = filter_
        context['table_matiere'] = table_matiere
        context['repartition_credits_chart'] = RepartitionCreditChart(filter_.qs)
        table_diplome = DiplomeTable(Diplome.objects.all(), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table_diplome)
        context['table_diplome'] = table_diplome
        table_departement = DepartementTable(Departement.objects.all(), exclude=exclude_columns(self.request.user))
        RequestConfig(self.request).configure(table_departement)
        context['table_departement'] = table_departement

        return context


class ProgrammeCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Programme
    fields = ['code', 'ordre', 'titre', 'titre_a', 'diplome', 'specialite', 'departement', 'description', 'assistant']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_formation'
    success_message = "Le programme a été bien créé."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_design')
        return form

    def get_context_data(self, **kwargs):
        context = super(ProgrammeCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter un programme'
        return context


class ProgrammeUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = Programme
    fields = ['code', 'ordre', 'concours', 'diplome', 'titre', 'titre_a', 'diplome', 'specialite', 'departement',
              'description', 'assistant']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_formation'
    success_message = 'Le programme a été bien modifié.'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_design')
        return form

    def get_context_data(self, **kwargs):
        context = super(ProgrammeUpdateView, self).get_context_data(**kwargs)
        context['titre'] = 'Modifier le programme'
        return context


class ProgrammeDetailView(DetailView):
    model = Programme
    template_name_suffix = '_detail'

    def get_context_data(self, **kwargs):
        context = super(ProgrammeDetailView, self).get_context_data(**kwargs)
        context['categorie_ue'] = dict(CAT_UE)
        return context


class DepartementUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = Departement
    fields = ['intitule', 'intitule_a', 'responsable', 'cycle_intitule', 'cycle_ordre', 'signature', 'reglement']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_departement'
    success_message = 'Le départmenet a été bien modifié.'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        # form.fields['signature']=forms.ImageField(label='Signature', required=False, widget=forms.FileInput(attrs={'class':"custom-file-input"}))
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_design')
        return form


class DepartementCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Departement
    fields = ['intitule', 'intitule_a', 'responsable', 'signature', 'reglement', 'cycle_intitule', 'cycle_ordre']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_departement'
    success_message = 'Le départmenet a bien été créé.'

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_design')
        return form

    def get_context_data(self, **kwargs):
        context = super(DepartementCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Créer un département'
        return context


class DepartementDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = Departement
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_departement'
    success_message = "Le département a été bien supprimé."

    def get_success_url(self):
        return reverse('programme_design')


class DiplomeCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    permission_required = ['scolar.add_diplome']
    template_name = 'scolar/create.html'
    model = Diplome
    fields = ['intitule', 'intitule_a', 'domaine', 'filiere']
    success_message = "Le diplôme a bien été créé."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_design') + '#diplomes'
        return form

    def get_context_data(self, **kwargs):
        context = super(DiplomeCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter un diplôme'
        return context


class DiplomeUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    permission_required = ['scolar.change_diplome']
    template_name = 'scolar/update.html'
    model = Diplome
    fields = ['intitule', 'intitule_a', 'domaine', 'filiere']
    success_message = "Le diplôme a bien été modifié."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_design')
        return form


class DiplomeDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = Diplome
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_diplome'
    success_message = "Le diplôme a bien éte supprimé"

    def get_success_url(self):
        return reverse('programme_design')


class MatiereDetailView(DetailView):
    model = Matiere
    template_name_suffix = '_detail'

    def get_context_data(self, **kwargs):
        context = super(MatiereDetailView, self).get_context_data(**kwargs)
        context['object'] = {}
        try:
            context['object']['matiere'] = Matiere.objects.get(id=self.kwargs.get('pk'))
            context['object'].update(
                get_competence_context(MatiereCompetenceElement.objects.filter(matiere=self.kwargs.get('pk'))))
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la construction de la matrice de compétence pour la matière")
        context['pdf'] = False
        return context


class MatiereDetailPDFView(PDFTemplateView):
    template_name = 'scolar/matiere_detail_pdf.html'
    cmd_options = {
        'orientation': 'Portrait',
        'page-size': 'A4',
    }

    def get_context_data(self, **kwargs):
        context = super(MatiereDetailPDFView, self).get_context_data(**kwargs)
        context['object'] = {}
        try:
            context['object']['matiere'] = Matiere.objects.get(id=self.kwargs.get('pk'))
            self.filename = str(context['object']['matiere']) + '.pdf'
            context['object'].update(
                get_competence_context(MatiereCompetenceElement.objects.filter(matiere=self.kwargs.get('pk'))))
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la construction de la matrice de compétence pour la matière")
        context['pdf'] = True
        return context


class MatiereDetailListPDFView(PDFTemplateView):
    template_name = 'scolar/matiere_detail_list_pdf.html'
    cmd_options = {
        'orientation': 'Portrait',
        'page-size': 'A4',
    }

    def get_context_data(self, **kwargs):
        context = super(MatiereDetailListPDFView, self).get_context_data(**kwargs)
        programme_ = Programme.objects.get(id=self.kwargs.get('programme_pk'))
        self.filename = "SYLLABUS_" + str(programme_) + ".pdf"
        context['object'] = programme_
        context['matieres'] = {}
        try:
            for periode in programme_.periodes.all():
                for ue in periode.ues.all():
                    for matiere_ in ue.matieres.all():
                        if not matiere_.code in context['matieres'].keys():
                            context['matieres'][matiere_.code] = {}
                            context['matieres'][matiere_.code]['matiere'] = matiere_
                            context['matieres'][matiere_.code].update(
                                get_competence_context(MatiereCompetenceElement.objects.filter(matiere=matiere_)))
            context['categorie_ue'] = dict(CAT_UE)
        except Exception:
            if settings.DEBUG:
                raise Exception
            else:
                messages.error(self.request,
                               "ERREUR: lors de la construction de la matrice de compétence pour les matière")
        context['pdf'] = True
        return context


class MatiereUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = Matiere
    fields = ['code', 'precision', 'pfe', 'mode_projet', 'ddc', 'titre', 'titre_a', 'titre_en', 'coef', 'credit',
              'edition', 'vh_cours', 'vh_td', 'pre_requis', 'objectifs', 'contenu', 'bibliographie', 'travail_perso']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_matiere'
    success_message = "La matière a bien été modifiée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = MatiereFormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        form.helper.add_input(Button('modifier', 'Définir Compétences', css_class='btn-warning',
                                     onclick="window.location.href='" + reverse('matiere_competence_update', kwargs={
                                         'matiere_pk': self.kwargs.get('pk')}) + "'"))
        self.success_url = self.request.META.get('HTTP_REFERER')
        return form

    def get_context_data(self, **kwargs):
        context = super(MatiereUpdateView, self).get_context_data(**kwargs)
        context['titre'] = 'Modifier la matière'
        return context


class MatiereCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Matiere
    fields = ['code', 'precision', 'pfe', 'mode_projet', 'ddc', 'titre', 'titre_a', 'titre_en', 'coef', 'credit',
              'edition', 'vh_cours', 'vh_td', 'pre_requis', 'objectifs', 'contenu', 'bibliographie', 'travail_perso']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_matiere'
    success_message = "La matière a bien été créée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = MatiereFormHelper()
        form.helper.add_input(Submit('submit', 'Enregistrer', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))

        self.success_url = reverse("programme_list")
        return form

    def get_context_data(self, **kwargs):
        context = super(MatiereCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Créer une nouvelle matière'
        return context


class MatiereCompetenceElementUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = MatiereCompetenceElement
    fields = ['niveau', ]
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_matierecompetenceelement'
    success_message = "L'élément de compétence a bien été modifié."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('matiere_competence_update', kwargs={'matiere_pk': self.kwargs.get('matiere_pk')})
        return form

    def get_context_data(self, **kwargs):
        context = super(MatiereCompetenceElementUpdateView, self).get_context_data(**kwargs)
        context['titre'] = 'Modifier Niveau d\'acquisition de l\'élément de compétence'
        return context


class MatiereCompetenceElementDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = MatiereCompetenceElement
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_matierecompetenceelement'
    success_message = "L'élément de compétence a bien été supprimé."

    def get_success_url(self):
        return reverse('matiere_competence_update', kwargs={'matiere_pk': self.kwargs.get('matiere_pk')})


def get_competence_context(matiere_competence_element_qs):
    # on construit ici la représentation matricielle des compétences:
    # ddc_list : en colonne la liste des domaines de connaissance
    # pgm_list : en colonne la liste des programmes (niveau d'études)
    # ce_list: en ligne la liste des éléments de compétence
    # ce_ddc_list: dans les cellules la liste des matières qui assurent cette élément de compétence
    # ce_pgm_list : dans les cellules la liste des matières qui assrent cet élement de compétence
    ddc_list = DomaineConnaissance.objects.all()
    pgm_list = Programme.objects.all().order_by('ordre')
    ce_ddc_list = {}
    ce_pgm_list = {}
    cf_list = {}

    for matiere_ce_ in matiere_competence_element_qs:
        competence_element_ = matiere_ce_.competence_element
        competence_ = competence_element_.competence
        competence_family_ = competence_.competence_family

        if not competence_family_.code in cf_list.keys():
            cf_list[competence_family_.code] = {
                'competence_family': competence_family_,
                'c_list': {},
                'nb_ce': 0
            }
        if not competence_.id in cf_list[competence_family_.code]['c_list'].keys():
            cf_list[competence_family_.code]['c_list'][competence_.id] = {
                'competence': competence_,
                'ce_list': [],
                'nb_ce': 0
            }
        if not competence_element_ in cf_list[competence_family_.code]['c_list'][competence_.id]['ce_list']:
            cf_list[competence_family_.code]['c_list'][competence_.id]['ce_list'].append(competence_element_)
            cf_list[competence_family_.code]['c_list'][competence_.id]['nb_ce'] += 1
            cf_list[competence_family_.code]['nb_ce'] += 1
            for ddc_ in ddc_list:
                key_ = str(competence_element_.id) + '_' + str(ddc_.id)
                ce_ddc_list[key_] = []
            for pgm_ in pgm_list:
                key_ = str(competence_element_.id) + '_' + str(pgm_.id)
                ce_pgm_list[key_] = []

        key_ = str(competence_element_.id) + '_' + str(matiere_ce_.matiere.ddc.id)
        ce_ddc_list[key_].append(matiere_ce_)

        for ue_ in matiere_ce_.matiere.matiere_ues.all():
            key_ = str(competence_element_.id) + '_' + str(ue_.periode.programme.id)
            ce_pgm_list[key_].append(matiere_ce_)

    context = {}
    context['ddc_list'] = ddc_list
    context['pgm_list'] = pgm_list
    context['cf_list'] = cf_list
    context['ce_ddc_list'] = ce_ddc_list
    context['ce_pgm_list'] = ce_pgm_list

    return context


def competence_list_view(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = CompetenceForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            form_data = form.cleaned_data
            competence_family_ = form_data['competence_family']
            competence_ = form_data['competence']
            competence_element_ = form_data['competence_element']

            if competence_element_:
                qs = MatiereCompetenceElement.objects.filter(competence_element__in=competence_element_).order_by(
                    'competence_element__competence__competence_family__code', 'competence_element__competence__code',
                    'competence_element__code', 'matiere__code')
            elif competence_:
                qs = MatiereCompetenceElement.objects.filter(competence_element__competence=competence_).order_by(
                    'competence_element__competence__competence_family__code', 'competence_element__competence__code',
                    'competence_element__code', 'matiere__code')
            elif competence_family_:
                qs = MatiereCompetenceElement.objects.filter(
                    competence_element__competence__competence_family=competence_family_).order_by(
                    'competence_element__competence__competence_family__code', 'competence_element__competence__code',
                    'competence_element__code', 'matiere__code')
            else:
                qs = MatiereCompetenceElement.objects.all().order_by(
                    'competence_element__competence__competence_family__code', 'competence_element__competence__code',
                    'competence_element__code', 'matiere__code')
            table = MatiereCompetenceElementTable(qs, exclude=exclude_columns(request.user))
            messages.success(request,
                             "Les éléments de compétence ont bien été sélectionnés. Vous pouvez les visualiser dans le tableau ci-bas.")
            messages.success(request,
                             "Vous pouvez visualiser la matrice de compétence construite avec ces éléments de compétence.")
    else:

        qs = MatiereCompetenceElement.objects.all().order_by('competence_element__competence__competence_family__code',
                                                             'competence_element__competence__code',
                                                             'competence_element__code', 'matiere__code')
        table = MatiereCompetenceElementTable(qs, exclude=exclude_columns(request.user))

        form = CompetenceForm()
        # messages.info(request, "Utilisez ce formulaire pour sélectionner les éléments de compétences et visualiser la matrice de compétence.")
        # messages.info(request, "Par défaut, tous les éléments de compétence de la catégorie choisie seront sélectionnés.")
    try:
        context = get_competence_context(qs)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: lors de la création de la matrice de compétence. Merci de le signaler à l'administrateur.")
    context['form'] = form
    context['table'] = table
    context['titre'] = 'Compétences développées à l\'issue de nos formations'
    return render(request, 'scolar/competence_matrice.html', context)


class ReferentielCompetenceView(TemplateView):
    template_name = 'scolar/referentiel_competence.html'
    titre = 'Référentiel de Compétences'

    def get_context_data(self, **kwargs):
        context = super(ReferentielCompetenceView, self).get_context_data(**kwargs)
        qs = MatiereCompetenceElement.objects.all().order_by('competence_element__competence__competence_family__code',
                                                             'competence_element__competence__code',
                                                             'competence_element__code', 'matiere__code')
        context.update(get_competence_context(qs))
        context['titre'] = self.titre
        matiere_list = {}
        for matiere_ in Matiere.objects.all().order_by('code'):
            matiere_list[matiere_.id] = {}
            matiere_list[matiere_.id]['matiere'] = matiere_
            matiere_list[matiere_.id].update(
                get_competence_context(MatiereCompetenceElement.objects.filter(matiere=matiere_)))

        context['matiere_list'] = matiere_list
        context['categorie_ue'] = dict(CAT_UE)

        return context


class MatriceCompetenceDDCView(ReferentielCompetenceView):
    template_name = 'scolar/matrice_competence_ddc.html'
    titre = 'Matrice des Compétences par Domaine de Connaissance'


class MatriceCompetenceNiveauView(ReferentielCompetenceView):
    template_name = 'scolar/matrice_competence_niveau.html'
    titre = 'Matrice des Compétences par Niveau d\'étude'


class CatalogueProgrammeView(ReferentielCompetenceView):
    template_name = 'scolar/catalogue_programme.html'
    titre = 'Catalogue des Programmes'


@login_required
@permission_required(['scolar.view_matierecompetenceelement', 'scolar.change_matierecompetenceelement',
                      'scolar.add_matierecompetenceelement'])
def matiere_competence_update_view(request, matiere_pk):
    # if this is a POST request we need to process the form data
    matiere_ = get_object_or_404(Matiere, id=matiere_pk)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = CompetenceForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                form_data = form.cleaned_data
                competence_family_ = form_data['competence_family']
                competence_ = form_data['competence']
                competence_element_list = form_data['competence_element']
                for competence_element_ in competence_element_list:
                    MatiereCompetenceElement.objects.get_or_create(matiere=matiere_,
                                                                   competence_element=competence_element_, defaults={
                            'matiere': matiere_,
                            'competence_element': competence_element_,
                            'niveau': 'B',
                        })
            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: lors de l'ajout des éléments de compétence à la matière. Merci de le signaler à l'administrateur")
            messages.success(request, "Les éléments de compétence sélectionnés ont bien été rajouté à la matière.")
    else:
        form = CompetenceForm()
        messages.info(request, "Merci de sélectionner les éléments de compétence à rajouter à la matière.")

    qs = MatiereCompetenceElement.objects.filter(matiere=matiere_).order_by(
        'competence_element__competence__competence_family__code', 'competence_element__competence__code',
        'competence_element__code', 'matiere__code')
    table = MatiereCompetenceElementTable(qs, exclude=exclude_columns(request.user))
    try:
        context = get_competence_context(qs)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: lors de la construction de la matrice de compétences. Merci de le signaler à l'administrateur.")
    context['form'] = form
    context['table'] = table
    context['titre'] = 'Compétences développées à l\'issue de nos formations'

    return render(request, 'scolar/competence_matrice.html', context)


class CompetenceFamilyListView(TemplateView):
    template_name = 'scolar/list.html'

    def get_context_data(self, **kwargs):
        context = super(CompetenceFamilyListView, self).get_context_data(**kwargs)
        table = CompetenceFamilyTable(CompetenceFamily.objects.all().order_by('code'),
                                      exclude=exclude_columns(self.request.user))

        RequestConfig(self.request).configure(table)
        context['titre'] = 'Familles de Compétences'
        context['table'] = table
        context['back'] = reverse('competence_list')
        if self.request.user.has_perm('scolar.add_competencefamily'):
            context['create_url'] = reverse('competence_family_create')
            context['create_btn'] = 'Famille Compétences'
        btn_list = {
            'Référentiel Compétences': reverse('referentiel_competence'),
            'Matrice Compétence / DDC': reverse('matrice_competence_ddc'),
            'Matrice Compétence / Niveau': reverse('matrice_competence_niveau')
        }
        context['btn_list'] = btn_list
        return context


class CompetenceFamilyCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = CompetenceFamily
    fields = ['code', 'intitule']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_competencefamily'
    success_message = "La famille de compétences a bien été créée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('competence_family_list')
        return form

    def get_context_data(self, **kwargs):
        context = super(CompetenceFamilyCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter une Famille de Compétences'
        return context


class CompetenceFamilyUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = CompetenceFamily
    fields = ['code', 'intitule']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_competencefamily'
    success_message = "La famille de compétence a bien été modifiée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('competence_family_list')
        return form


class CompetenceFamilyDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = CompetenceFamily
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_competencefamily'
    success_message = "La famille de compétence a bien été supprimée."

    def get_success_url(self):
        return reverse('competence_family_list')


class CompetenceListView(TemplateView):
    template_name = 'scolar/list.html'

    def get_context_data(self, **kwargs):
        context = super(CompetenceListView, self).get_context_data(**kwargs)
        table = CompetenceTable(
            Competence.objects.filter(competence_family=self.kwargs.get('competence_family_pk')).order_by('code'),
            exclude=exclude_columns(self.request.user))

        RequestConfig(self.request).configure(table)
        context['titre'] = 'Liste de Compétences de la famille ' + self.kwargs.get('competence_family_pk')
        context['table'] = table
        context['back'] = reverse('competence_family_list')
        if self.request.user.has_perm('scolar.add_competence'):
            context['create_url'] = reverse('competence_create',
                                            kwargs={'competence_family_pk': self.kwargs.get('competence_family_pk')})
            context['create_btn'] = 'Compétence'
        return context


class CompetenceCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Competence
    fields = ['code', 'competence_family', 'intitule']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_competence'
    success_message = "La compétence a bien été créée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['competence_family'] = forms.ModelChoiceField(
            queryset=CompetenceFamily.objects.filter(code=self.kwargs.get('competence_family_pk')), initial=0)
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('competence_list',
                                   kwargs={'competence_family_pk': self.kwargs.get('competence_family_pk')})
        return form

    def get_context_data(self, **kwargs):
        context = super(CompetenceCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter une Compétences à ' + self.kwargs.get('competence_family_pk')
        return context


class CompetenceUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = Competence
    fields = ['code', 'competence_family', 'intitule']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_competence'
    success_message = "La compétence a bien été modifiée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('competence_list',
                                   kwargs={'competence_family_pk': self.kwargs.get('competence_family_pk')})
        return form


class CompetenceDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = Competence
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_competence'
    success_message = "La compétence a bien été supprimée."

    def get_success_url(self):
        return reverse('competence_list', kwargs={'competence_family_pk': self.kwargs.get('competence_family_pk')})


class CompetenceElementListView(TemplateView):
    template_name = 'scolar/list.html'

    def get_context_data(self, **kwargs):
        context = super(CompetenceElementListView, self).get_context_data(**kwargs)
        table = CompetenceElementTable(
            CompetenceElement.objects.filter(competence=self.kwargs.get('competence_pk')).order_by('code'),
            exclude=exclude_columns(self.request.user))
        competence_ = get_object_or_404(Competence, id=self.kwargs.get('competence_pk'))
        RequestConfig(self.request).configure(table)
        context['titre'] = 'Liste des éléments de Compétences'
        context['table'] = table
        context['back'] = reverse('competence_list',
                                  kwargs={'competence_family_pk': competence_.competence_family.code})
        if self.request.user.has_perm('scolar.add_competenceelement'):
            context['create_url'] = reverse('competence_element_create',
                                            kwargs={'competence_pk': self.kwargs.get('competence_pk')})
            context['create_btn'] = 'Element de Compétence'
        return context


class CompetenceElementCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = CompetenceElement
    fields = ['code', 'competence', 'intitule', 'type', 'objectif']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_competenceelement'
    success_message = "L'étément de compétence a bien été créé."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['competence'] = forms.ModelChoiceField(
            queryset=Competence.objects.filter(id=self.kwargs.get('competence_pk')), initial=0)
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('competence_element_list',
                                   kwargs={'competence_pk': self.kwargs.get('competence_pk')})
        return form

    def get_context_data(self, **kwargs):
        context = super(CompetenceElementCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter un Element de Compétence'
        return context


class CompetenceElementUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = CompetenceElement
    fields = ['code', 'competence', 'intitule', 'type', 'objectif']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_competenceelement'
    success_message = "L'étément de compétence a bien été modifié."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('competence_element_list',
                                   kwargs={'competence_pk': self.kwargs.get('competence_pk')})
        return form


class CompetenceElementDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = CompetenceElement
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_competenceelement'
    success_message = "L'étément de compétence a bien été supprimé."

    def get_success_url(self):
        return reverse('competence_element_list', kwargs={'competence_pk': self.kwargs.get('competence_pk')})


class PeriodeDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = Periode
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_periode'
    success_message = "Le semestre a bien été supprimé."

    def get_success_url(self):
        return reverse('programme_detail', kwargs={'pk': str(self.kwargs.get('programme_pk'))})


class UEDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = UE
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_ue'
    success_message = "L'UE a bien été supprimée.."

    def get_success_url(self):
        return reverse('programme_detail', kwargs={'pk': str(self.kwargs.get('programme_pk'))})


class UEUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = UE
    fields = ['code', 'type', 'nature', 'periode', 'matieres']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_ue'
    success_message = "L'UE a bien été modifiée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['periode'] = forms.ModelChoiceField(
            queryset=PeriodeProgramme.objects.filter(programme=self.kwargs.get('programme_pk')),
            initial=self.kwargs.get('periode_pk'))
        form.fields['matieres'] = forms.ModelMultipleChoiceField(queryset=Matiere.objects.all().order_by('code'),
                                                                 widget=
                                                                 ModelSelect2MultipleWidget(
                                                                     Model=Matiere,
                                                                     search_fields=['code__icontains',
                                                                                    'titre__icontains']
                                                                 ),
                                                                 help_text="Tapez le nom de la matière. Vous pouvez sélectionner plusieurs. Tapez deux espaces pour avoir la liste complète")
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_detail', kwargs={'pk': str(self.kwargs.get('programme_pk'))})
        return form


class ResultatUEDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = ResultatUE
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_resultatue'
    success_message = "L'UE a bien été supprimée.."

    def get_success_url(self):
        return reverse('releve_notes', kwargs={'inscription_pk': str(self.kwargs.get('inscription_pk'))})


class PeriodeProgrammeCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = PeriodeProgramme
    fields = ['periode', 'programme', 'code']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_periodeprogramme'
    success_message = "Le semestre a bien été créé."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['programme'] = forms.ModelChoiceField(
            queryset=Programme.objects.filter(id=self.kwargs.get('programme_pk')), initial=0)
        form.fields['periode'] = forms.ModelChoiceField(queryset=Periode.objects.all())
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_detail', kwargs={'pk': self.kwargs.get('programme_pk')})
        return form

    def get_context_data(self, **kwargs):
        context = super(PeriodeProgrammeCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter une période'
        return context


class PeriodeProgrammeUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = PeriodeProgramme
    fields = ['periode', 'programme', 'code']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_periodeprogramme'
    success_message = "Le semestre a bien été modifié."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['programme'] = forms.ModelChoiceField(
            queryset=Programme.objects.filter(id=self.kwargs.get('programme_pk')), initial=0)
        form.fields['periode'] = forms.ModelChoiceField(queryset=Periode.objects.all())
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_detail', kwargs={'pk': self.kwargs.get('programme_pk')})
        return form


class PeriodeProgrammeDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = PeriodeProgramme
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_periodeprogramme'
    success_message = "La période a bien été supprimée."

    def get_success_url(self):
        return reverse('programme_detail', kwargs={'pk': str(self.kwargs.get('programme_pk'))})


class PeriodeCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = Periode
    fields = ['code', 'session', 'ordre', 'nb_semaines']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_periode'
    success_message = "Le semestre a bien été créé."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_design')
        return form

    def get_context_data(self, **kwargs):
        context = super(PeriodeCreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter une période'
        return context


class PeriodeUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    model = Periode
    fields = ['code', 'ordre', 'session', 'nb_semaines']
    template_name = 'scolar/update.html'
    permission_required = 'scolar.change_periode'
    success_message = "Le semestre a bien été modifié."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-primary'))
        self.success_url = reverse('programme_design')
        return form


class UECreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    model = UE
    fields = ['code', 'type', 'nature', 'periode', 'matieres']
    template_name = 'scolar/create.html'
    permission_required = 'scolar.add_ue'
    success_message = "L'UE a bien été créée."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['periode'] = forms.ModelChoiceField(
            queryset=PeriodeProgramme.objects.filter(id=self.kwargs.get('periode_pk')), initial=0)
        form.fields['matieres'] = forms.ModelMultipleChoiceField(queryset=Matiere.objects.all().order_by('code'),
                                                                 widget=
                                                                 ModelSelect2MultipleWidget(
                                                                     Model=Matiere,
                                                                     search_fields=['code__icontains',
                                                                                    'titre__icontains']
                                                                 ),
                                                                 help_text="Tapez le nom de la matière. Vous pouvez sélectionner plusieurs. Tapez deux espaces pour avoir la liste complète")
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('programme_detail', kwargs={'pk': str(self.kwargs.get('programme_pk'))})
        return form

    def get_context_data(self, **kwargs):
        context = super(UECreateView, self).get_context_data(**kwargs)
        context['titre'] = 'Ajouter une UE'
        return context


@login_required
def absencesform(request, activite_pk, groupe_pk):
    activite_ = get_object_or_404(Activite, id=activite_pk)
    if request.user.is_etudiant():
        messages.error(request, "Vous n'êtes pas autorisés à excécuter cette opération")
        return redirect('/accounts/login/?next=%s' % request.path)
    elif request.user.is_enseignant():
        if not assure_module(request.user.enseignant, activite_.module):
            messages.error(request, "Vous n'êtes pas autorisés à excécuter cette opération")
            return redirect('/accounts/login/?next=%s' % request.path)

        # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = AbsencesForm(groupe_pk, activite_.module.id, request.POST)
        # check whether it's valid:
        if form.is_valid():
            try:
                # process the data in form.cleaned_data as required
                data = form.cleaned_data
                seance_, created = Seance.objects.get_or_create(activite=activite_.id, date=data['seance_date'],
                                                                rattrapage=data['seance_rattrapage'], defaults={
                        'activite': activite_,
                        'date': data['seance_date'],
                        'rattrapage': data['seance_rattrapage']
                    })
                absence_list = ''
                for matricule_ in data['absence_list']:
                    etudiant_ = get_object_or_404(Etudiant, matricule=matricule_)
                    #                 if data[inscrit]==True:
                    #                     etudiant_=get_object_or_404(Etudiant,matricule=inscrit)
                    absence_etudiant_, created = AbsenceEtudiant.objects.get_or_create(etudiant=etudiant_,
                                                                                       seance=seance_, defaults={
                            'etudiant': etudiant_,
                            'seance': seance_
                        })
                    absence_list += str(etudiant_) + '\n'

            except Exception:
                if settings.DEBUG:
                    raise Exception
                else:
                    messages.error(request,
                                   "ERREUR: Le signalement des absences s'est terminé avec echec. Merci de le signaler à l'administrateur.")
                    return HttpResponseRedirect(reverse('assiduite', kwargs={'activite_pk': seance_.activite.id}))
            messages.success(request, "Le signalement des absences s'est terminé avec succès!")
            # envoyer un message à l'enseignant
            email = EmailMessage('[Talents] Absences Signalées en ' + str(seance_),
                                 'Bonjour ' + str(request.user.enseignant.prenom) + ',\n' +
                                 'Nous confirmons le signalement des absences suivantes \n' +
                                 absence_list +
                                 'Les concernés ont été notifiés et invités à justifier leur absence dans les 48h\n'
                                 'Bien cordialement.\n' +
                                 'Département', to=[request.user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)

            # redirect to a new URL:
            return HttpResponseRedirect(reverse('assiduite', kwargs={'activite_pk': seance_.activite.id}))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = AbsencesForm(groupe_pk, activite_.module.id)
        messages.info(request, "Merci de cocher les étudiants absents.")
    return render(request, 'scolar/import.html', {'form': form, 'titre': "Fiche d'absences"})


@receiver(post_save, sender=AbsenceEtudiant)
def email_absence_etudiant(sender, update_fields, instance, created, **kwargs):
    if created:
        nb_absences = instance.nb_absences()
        if nb_absences < 3:
            email = EmailMessage(str(nb_absences) + ' Absences Signalées en ' + str(instance.seance.activite),
                                 'Bonjour,\n' +
                                 'Nous espérons que vous allez bien!\n Nous vous informons qu\'une nouvelle absence en ' + str(
                                     instance.seance.activite) +
                                 ' a été signalée\n' +
                                 'Veuillez vous rapprocher de la surveillace (' + str(
                                     instance.seance.activite.module.formation.programme.assistant.user.email) +
                                 ') dans les 48h pour justifier votre absence.\n' +
                                 'Sinon, vous allez vous exposez à des sanctions.\n' +
                                 'Merci de préciser dans votre justification le module er la date de l\'absence' +
                                 'Bien cordialement.\n' +
                                 'Département', to=[instance.etudiant.user.email])
        elif nb_absences < 5:
            email = EmailMessage('AVERTISSEMENT & CONVOCATION ' + str(
                nb_absences) + ' Absences Signalées en ' + instance.seance.activite.module.matiere.code,
                                 'Matricule: ' + instance.etudiant.matricule + '\n' +
                                 'Nom & Prénoms: ' + instance.etudiant.nom + ' ' + instance.etudiant.prenom + '\n' +
                                 'Année d\'études: ' + str(instance.seance.activite.module.formation) + '\n' +
                                 'Email: ' + instance.etudiant.user.email + '\n' +
                                 'Tel: ' + str(instance.etudiant.tel) + '\n\n\n'
                                                                        'Bonjour,\n' +
                                 'Nous espérons que vous allez bien!\n' +
                                 'Nous vous informons que ' + str(
                                     nb_absences) + ' absences au module ' + instance.seance.activite.module.matiere.code + ' ont été signalées\n' +
                                 'Ceci est un AVERTISSEMENT.\n' +
                                 'Veuillez vous rapprocher du Chef de Département pour clarifier votre situation.\n' +
                                 'Nous vous rappelons que la réglementation des études stipule l\'exclusion d\'une matière dans le cas de:\n' +
                                 '3 absences consécutives non justifiées, ou\n' +
                                 '5 absences mêmes justifiées.\n' +
                                 'Bien cordialement.\n' +
                                 'Département', to=[instance.etudiant.user.email,
                                                    instance.seance.activite.module.formation.programme.departement.responsable.user.email] + [
                                                       x.user.email for x in
                                                       instance.seance.activite.assuree_par.all()])
        else:
            email = EmailMessage('EXCLUSION suite à ' + str(
                nb_absences) + ' Absences Signalées en ' + instance.seance.activite.module.matiere.code,
                                 'Matricule: ' + instance.etudiant.matricule + '\n' +
                                 'Nom & Prénoms: ' + instance.etudiant.nom + ' ' + instance.etudiant.prenom + '\n' +
                                 'Année d\'études: ' + str(instance.seance.activite.module.formation) + '\n' +
                                 'Email: ' + instance.etudiant.user.email + '\n' +
                                 'Tel: \n\n\n'
                                 'Bonjour,\n' +
                                 'Nous espérons que vous allez bien!\n' +
                                 'Nous vous informons que ' + str(
                                     nb_absences) + ' absences au module ' + instance.seance.activite.module.matiere.code + ' ont été signalées\n' +
                                 'Nous vous rappelons que la réglementation des études stipule l\'exclusion d\'une matière dans le cas de:\n' +
                                 '3 absences consécutives non justifiées, ou\n' +
                                 '5 absences mêmes justifiées.\n' +
                                 'Veuillez donc vous rapprocher du Département pour clarifier votre situation et demander le cas échéant un billet d\'accès en salle.'
                                 'Si vous êtes redoublant ou en 1CP, nous vous conseillons d\'entamer vos prospections de réorientation dès maintenant car il est difficile de trouver des places à l\'université en mois de septembre.\n' +
                                 'Bien cordialement.\n'
                                 'Département', to=[instance.etudiant.user.email,
                                                    instance.seance.activite.module.formation.programme.departement.responsable.user.email] +
                                                   settings.STAFF_EMAILS['scolarite'] + settings.STAFF_EMAILS[
                                                       'direction'])
            # basculer l'état d'inscription vers ABANDON
            # inscription_=Inscription.objects.get(etudiant=instance.etudiant, formation__annee_univ__encours=True)
            # inscription_.decision_jury__startswith='F'
            # inscription_.save(update_fields=['decision_jury'])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)
    elif instance.justif:
        email = EmailMessage('[Talents] Justification Absence en ' + str(instance.seance),
                             'Bonjour ' + instance.etudiant.prenom + ',\n' +
                             'Nous vous informons que Talents a enregistré votre justification de votre absence en:\n' +
                             str(instance.seance) + '\n' +
                             'Bien cordialement.\n' +
                             'Département', to=[instance.etudiant.user.email])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)


@login_required
def export_notes(request, groupe_pk, module_pk):
    if request.user.is_etudiant():
        return redirect('/accounts/login/?next=%s' % request.path)

    try:
        # Create the HttpResponse object with the appropriate CSV header.
        groupe = get_object_or_404(Groupe, id=groupe_pk)
        module = get_object_or_404(Module, id=module_pk)
        resultat_list = Resultat.objects.filter(module=module_pk,
                                                resultat_ue__inscription_periode__groupe=groupe_pk).order_by(
            'inscription__etudiant__nom', 'inscription__etudiant__prenom')
        header = ['Matricule', 'Nom', 'Prenom', 'Nb Absences', 'Situation', 'Acquis']
        evaluation_list = module.evaluations.all()
        for eval_ in evaluation_list:
            header.append(eval_.type)
        if module.formation.archive or not evaluation_list.exists():
            header.append('Moy' + module.matiere.code)
        sheet = Dataset()
        sheet.headers = header

        for resultat_ in resultat_list:
            row_ = []
            row_.append(resultat_.inscription.etudiant.matricule)
            row_.append(resultat_.inscription.etudiant.nom)
            row_.append(resultat_.inscription.etudiant.prenom)
            row_.append(resultat_.module.nb_absences(resultat_.inscription.etudiant))
            row_.append(dict(DECISIONS_JURY)[resultat_.inscription.decision_jury])
            row_.append('Oui' if resultat_.acquis else 'Non')
            for eval_ in evaluation_list:
                note_, created = Note.objects.get_or_create(resultat=resultat_, evaluation=eval_,
                                                            defaults={'resultat': resultat_, 'evaluation': eval_,
                                                                      'note': 0})
                row_.append(note_.note)
            if module.formation.archive or not evaluation_list.exists():
                row_.append(resultat_.moy)
            sheet.append(row_)

        filename = str(module.matiere.code) + '_' + str(groupe) + '.xlsx'
        filename = filename.replace(' ', '_')

        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=' + filename + ";"
        response.write(sheet.xlsx)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: Il y a eu une erreur lors de l'export du fichier des notes. Merci de le signaler à l'administrateur.")
    return response


@login_required
def export_pfe_list(request):
    if not (request.user.is_stage() or request.user.is_top_management()):
        return redirect('/accounts/login/?next=%s' % request.path)

    try:
        # Create the HttpResponse object with the appropriate CSV header.
        pfe_list = PFE.objects.filter(Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
                                      reserve_pour__isnull=False).distinct()
        header = ['Groupe', 'ID', 'Matricule', 'Nom', 'Prenom', 'Specialite', 'Promoteur', 'Coencadrants', 'Titre',
                  'Organisme', 'Pays', ]
        sheet = Dataset()
        sheet.headers = header

        for pfe_ in pfe_list:
            row_ = []
            if pfe_.groupe:
                row_.append(pfe_.groupe.code)
            else:
                row_.append('')
            row_.append(str(pfe_.id))
            matricule_ = ''
            nom_ = ''
            prenom_ = ''
            specialite_ = ''
            for inscription_ in pfe_.reserve_pour.all():
                matricule_ += inscription_.etudiant.matricule + '\n'
                nom_ += inscription_.etudiant.nom + '\n'
                prenom_ += inscription_.etudiant.prenom + '\n'
                specialite_ += inscription_.formation.programme.specialite.code + '\n'
            row_.append(matricule_)
            row_.append(nom_)
            row_.append(prenom_)
            row_.append(specialite_)
            row_.append(pfe_.promoteur)
            coencadrants_ = ''
            for enseignant_ in pfe_.coencadrants.all():
                coencadrants_ += str(enseignant_) + '\n'
            row_.append(coencadrants_)

            row_.append(pfe_.intitule)
            row_.append(str(pfe_.organisme))
            row_.append(pfe_.organisme.pays.nom)
            sheet.append(row_)

        filename = 'Liste_PFE_Validés.xlsx'

        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=' + filename + ";"
        response.write(sheet.xlsx)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request, "ERREUR: Il y a eu une erreur lors de l'export du fichier des PFE validés")
    return response


@login_required
def export_etudiant_pfe_list(request, formation_pk):
    if not (request.user.is_stage() or request.user.is_top_management()):
        return redirect('/accounts/login/?next=%s' % request.path)

    try:
        # Create the HttpResponse object with the appropriate CSV header.
        formation_ = get_object_or_404(Formation, id=formation_pk)
        inscription_list = Inscription.objects.filter(formation=formation_pk).order_by('etudiant__nom',
                                                                                       'etudiant__prenom')
        header = ['Matricule', 'Nom', 'Prenom', 'Situation', 'ID_PFE ', 'Promoteur', 'Coencadrants', 'Titre',
                  'Organisme', 'Pays', 'Validation']
        sheet = Dataset()
        sheet.headers = header

        for inscription_ in inscription_list:
            pfe_list = PFE.objects.filter(reserve_pour__etudiant=inscription_.etudiant).order_by('id')
            if pfe_list.exists():
                for pfe_ in pfe_list:
                    row_ = []
                    row_.append(inscription_.etudiant.matricule)
                    row_.append(inscription_.etudiant.nom)
                    row_.append(inscription_.etudiant.prenom)
                    row_.append(dict(DECISIONS_JURY)[inscription_.decision_jury])
                    row_.append(pfe_.id)
                    row_.append(pfe_.promoteur)
                    coencadrants = ''
                    for coencadrant_ in pfe_.coencadrants.all():
                        coencadrants += str(coencadrant_) + ' + '
                    row_.append(coencadrants)
                    row_.append(pfe_.intitule)
                    row_.append(pfe_.organisme.sigle)
                    row_.append(pfe_.organisme.pays.nom)
                    row_.append(dict(STATUT_VALIDATION)[pfe_.statut_validation])
                    sheet.append(row_)
            else:
                row_ = []
                row_.append(inscription_.etudiant.matricule)
                row_.append(inscription_.etudiant.nom)
                row_.append(inscription_.etudiant.prenom)
                row_.append(dict(DECISIONS_JURY)[inscription_.decision_jury])
                row_.append(0)
                row_.append('')
                row_.append('')
                row_.append('')
                row_.append('')
                row_.append('')
                row_.append('')
                sheet.append(row_)
        filename = 'Liste_Etudiant_PFE_' + str(formation_) + '.xlsx'.replace(' ', '_')

        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=' + filename + ";"
        response.write(sheet.xlsx)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: Il y a eu une erreur lors de l'export du fichier des Etudiant - PFE validés")
    return response


@login_required
def export_fiche_eval_pfe(request, groupe_pk, module_pk):
    try:
        # Create the HttpResponse object
        groupe = get_object_or_404(Groupe, id=groupe_pk)
        module = get_object_or_404(Module, id=module_pk)
        resultat_list = Resultat.objects.filter(module=module_pk,
                                                resultat_ue__inscription_periode__groupe=groupe_pk).order_by(
            'inscription__etudiant__nom', 'inscription__etudiant__prenom')

        # create the DataBook object that will comprise the different information and evaluation sheets
        book = Databook()

        # Create then add ADMINISTRATION information sheet
        sheet = Dataset(title="ADMINISTRATION")
        sheet.append(["PARTIE RESERVEE A L'ADMINISTRATION", " ", " "])
        sheet.append([" ", " ", " "])
        sheet.append(['PROMOTION:', str(module.formation.annee_univ.annee_univ) + '/' + str(
            module.formation.annee_univ.annee_suivante()), " "])
        sheet.append(['CODE PFE: ', groupe.code, " "])
        sheet.append([" ", " ", " "])
        sheet.append(['Noms et Prénoms des Candidats', 'Matricule', 'Option'])
        for resultat_ in resultat_list:
            sheet.append([resultat_.inscription.etudiant.nom + ' ' + resultat_.inscription.etudiant.prenom,
                          resultat_.inscription.etudiant.matricule,
                          resultat_.inscription.formation.programme.specialite.intitule + ' -- ' + resultat_.inscription.formation.programme.specialite.code])
        sheet.append([" ", " ", " "])
        sheet.append(['Intitulé du mémoire: ', " ", " "])
        sheet.append([groupe.pfe.intitule, " ", " "])
        sheet.append([" ", " ", " "])
        sheet.append(['Date de soutenance: ', groupe.soutenance.date.strftime("%d/%m/%Y"), " "])
        sheet.append([" ", " ", " "])
        sheet.append(['COMPOSITION DU JURY', " ", " "])
        if groupe.soutenance.president:
            sheet.append(['Président', str(groupe.soutenance.president), " "])
        if groupe.soutenance.examinateur:
            sheet.append(['Examinateur', str(groupe.soutenance.examinateur), " "])
        if groupe.soutenance.rapporteur:
            sheet.append(['Rapporteur', str(groupe.soutenance.rapporteur), " "])
        if groupe.soutenance.coencadrant:
            sheet.append(['Coencadrant', str(groupe.soutenance.coencadrant), " "])
        if groupe.soutenance.assesseur1:
            sheet.append(['Assesseur 1', str(groupe.soutenance.assesseur1), " "])
        if groupe.soutenance.assesseur2:
            sheet.append(['Assesseur 2', str(groupe.soutenance.assesseur2), " "])

        book.add_sheet(sheet)

        # add evaluations to the book
        for eval_ in module.evaluations.all():
            sheet = Dataset(title=eval_.type)
            sheet.append(['FICHE DE NOTATION DU PFE, VOLET: ' + eval_.type, " ", " "])
            for resultat_ in resultat_list:
                sheet.append([" ", " ", " "])
                sheet.append(["EVALUATION DE: " + str(resultat_.inscription.etudiant), " ", " "])
                sheet.append([" ", " ", " "])
                sheet.append(['Elément de Compétence', 'Commun', 'Appréciation'])
                note_, created = Note.objects.get_or_create(resultat=resultat_, evaluation=eval_, defaults={
                    'resultat': resultat_,
                    'evaluation': eval_,
                    'note': 0
                })

                for competence_ in eval_.competence_elements.all().order_by('commune_au_groupe',
                                                                            'competence_element__code'):
                    note_competence_element, created = NoteCompetenceElement.objects.get_or_create(
                        evaluation_competence_element=competence_, note_globale=note_, defaults={
                            'evaluation_competence_element': competence_,
                            'note_globale': note_,
                            'valeur': 0,
                        })
                    sheet.append([competence_.competence_element.intitule,
                                  'OUI' if competence_.commune_au_groupe else 'NON',
                                  dict(COMPETENCE_EVAL[eval_.type])[
                                      str(round(decimal.Decimal(note_competence_element.valeur), 2))]
                                  ])
            book.add_sheet(sheet)

        filename = 'FICHE_EVALUATION_' + str(groupe.code) + '.xlsx'

        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=' + filename + ";"
        response.write(book.export('xlsx'))
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: Il y a eu une erreur lors de l'export du fichier d'évaluation du PFE. Merci de le signaler à l'administrateur.")
    return response


@login_required
def notes_clear_view(request, inscription_periode_pk):
    inscription_periode_ = get_object_or_404(InscriptionPeriode, id=inscription_periode_pk)
    if request.user.is_direction():
        pass
    else:
        messages.error(request, "Vous n'êtes pas autorisé à exécuter cette opération.")
        return HttpResponseRedirect(
            reverse('releve_notes', kwargs={'inscription_pk': inscription_periode_.inscription.id}))
    try:
        Note.objects.filter(resultat__resultat_ue__inscription_periode=inscription_periode_pk).delete()
        Resultat.objects.filter(resultat_ue__inscription_periode=inscription_periode_pk).update(
            moy=0,
            moy_post_delib=0,
            ects='F',
            acquis=False
        )
        InscriptionPeriode.objects.filter(id=inscription_periode_pk).update(
            moy=0,
            rang=0,
            ne=inscription_periode_.nb_matieres()
        )
        Inscription.objects.filter(id=inscription_periode_.inscription.id).update(
            moy=inscription_periode_.inscription.moyenne(),
            rang=inscription_periode_.inscription.ranking()
        )
        # redirect to a new URL:
        messages.success(request, "Le semestre a été bien ré-initialisé")
        return HttpResponseRedirect(
            reverse('releve_notes', kwargs={'inscription_pk': inscription_periode_.inscription.id}))

    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request, "ERREUR: lors de la ré-initialisation du semestre")
            return HttpResponseRedirect(
                reverse('releve_notes', kwargs={'inscription_pk': inscription_periode_.inscription.id}))


@login_required
def acquis_clear_view(request, resultat_pk):
    resultat_ = get_object_or_404(Resultat, id=resultat_pk)
    if request.user.is_direction():
        pass
    else:
        messages.error(request, "Vous n'êtes pas autorisé à exécuter cette opération.")
        return HttpResponseRedirect(reverse('releve_notes', kwargs={'inscription_pk': resultat_.inscription.id}))

    try:
        Note.objects.filter(resultat=resultat_pk).delete()
        Resultat.objects.filter(id=resultat_pk).update(
            moy=0,
            moy_post_delib=0,
            ects='F',
            acquis=False
        )
        # redirect to a new URL:
        messages.success(request, "La note a été bien ré-initialisée")
        return HttpResponseRedirect(reverse('releve_notes', kwargs={'inscription_pk': resultat_.inscription.id}))

    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: lors de la ré-initialisation de la note. veuillez la signaler à l'administrateur.")
            return HttpResponseRedirect(reverse('releve_notes', kwargs={'inscription_pk': resultat_.inscription.id}))


@login_required
def modules_acquis_view(request, inscription_pk):
    if request.user.is_direction():
        pass
    else:
        messages.error(request, "Vous n'êtes pas autorisé à exécuter cette opération.")
        return HttpResponseRedirect(reverse('releve_notes', kwargs={'inscription_pk': inscription_pk}))

    try:
        # parcourir tous les résultats de l'inscription en cours
        for resultat_ in Resultat.objects.filter(inscription=inscription_pk):
            # Si module acquis alors copier l'ancien dans le nouveau
            old_resultat_ = Resultat.objects.filter(inscription__etudiant=resultat_.inscription.etudiant,
                                                    module__matiere__code=resultat_.module.matiere.code,
                                                    inscription__formation__annee_univ__annee_univ__lt=resultat_.inscription.formation.annee_univ.annee_univ,
                                                    acquis=True).order_by(
                '-inscription__formation__annee_univ__annee_univ')
            if old_resultat_.exists():
                old_resultat_ = old_resultat_[0]
                resultat_.moy = old_resultat_.moy
                resultat_.moy_post_delib = old_resultat_.moy_post_delib
                resultat_.ecst = old_resultat_.ects
                resultat_.acquis = True
                resultat_.save(update_fields=['moy', 'moy_post_delib', 'ects', 'acquis'])

        messages.success(request, "Les modules acquis ont bien été insrés dans cette inscription")
        return HttpResponseRedirect(reverse('releve_notes', kwargs={'inscription_pk': inscription_pk}))

    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: lors de l'insertion des modules acquis. Veuillez la signaler à l'administrateur.")
            return HttpResponseRedirect(reverse('releve_notes', kwargs={'inscription_pk': inscription_pk}))


@login_required
def note_update(request, matiere_pk, groupe_pk):
    # Il faudra refaire le traitement des données du formuliare pour n'enregistrer
    # que les données ayant changé et pas toutes (form.changed_data) pour éviter des
    # problèmes de performance

    module_ = get_object_or_404(ModulesSuivis, groupe=groupe_pk, module__matiere=matiere_pk).module
    groupe_ = get_object_or_404(Groupe, id=groupe_pk)
    liste_inscrits = Inscription.objects.filter(inscription_periodes__groupe=groupe_.id,
                                                inscription_periodes__periodepgm=module_.periode).order_by(
        'etudiant__nom', 'etudiant__prenom')
    liste_evaluations = Evaluation.objects.filter(module=module_.id)

    # Si la formation est archivée ou si un PV est déjà établit alors ne pas autoriser la modification
    if request.user.is_direction():
        pass
    elif module_.formation.archive or module_.pv_existe():
        messages.error(request,
                       "Il n'est plus possible de modifier les notes car un PV a été établit ou la saisie est clôturée.")
        return HttpResponseRedirect(reverse('note_list', kwargs={'groupe_pk': groupe_pk, 'matiere_pk': matiere_pk}))
    elif request.user.is_enseignant():
        if not assure_module_groupe(request.user.enseignant, module_, groupe_):
            messages.error(request, "Vous n'êtes pas autorisé à effectuer cette opération")
            return redirect('/accounts/login/?next=%s' % request.path)
    else:
        messages.error(request, "Vous n'avez pas les permissions d'accès à cette page.")
        return redirect('/accounts/login/?next=%s' % request.path)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = NotesUpdateForm(groupe_pk, module_.id, request, request.POST)
        # check whether it's valid:
        if form.is_valid():
            if module_.formation.archive:
                messages.error(request, "La saisie des notes est clôturée pour cette formation.")
            else:
                # Vérifier que l'OTP est correct
                if not settings.SMS_ENABLED or request.user.is_direction() or request.user.enseignant.check_otp(
                        form.cleaned_data['otp']):
                    # submit as background task
                    t = threading.Thread(target=task_note_update, args=[form, module_, groupe_, request.user])
                    t.setDaemon(True)
                    t.start()
                    messages.info(request,
                                  "Votre demande d'enregistrement des notes a été prise en compte. Une notification vous sera transmise.")
                else:
                    messages.error(request, "Le Code Secret saisi est incorrect.")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('note_list', kwargs={'groupe_pk': groupe_pk, 'matiere_pk': matiere_pk}))
            # if a GET (or any other method) we'll create a blank form
    else:
        if not request.user.enseignant.tel:
            messages.error(request,
                           "Votre numéro de téléphone n'est pas enregsitré dans la base. Il est nécessaire pour vous envoyer un Mot de passe à Usage Unique.")
            messages.info(request,
                          "Merci de communiquer votre numéro à l'administration afin que vous puissiez saisir les notes.")
            return HttpResponseRedirect(
                reverse('note_list', kwargs={'groupe_pk': groupe_pk, 'matiere_pk': module_.matiere.id}))
        else:
            form = NotesUpdateForm(groupe_pk, module_.id, request)
            messages.info(request, "Merci de renseigner les notes dans le formulaire")
            messages.warning(request,
                             "Si vous ne retrouvez pas les colonnes correspondantes aux évaluations prévues, merci de demander au coordinateur(trice) d'introduire la formule de calcul.")
            return render(request, 'scolar/note_update.html',
                          {'form': form, 'liste_inscrits': liste_inscrits, 'liste_evaluations': liste_evaluations,
                           'module_': module_, 'groupe_': groupe_,
                           'sms': settings.SMS_ENABLED and not request.user.is_direction(),
                           'url': settings.SMS_URL,
                           'function': 'sms_send',
                           'apikey': settings.SMS_API_KEY,
                           'userkey': settings.SMS_USER_KEY,
                           'message': 'Talents Code Secret: ' + request.user.enseignant.set_otp(),
                           'message_priority': 'Urgent',
                           'to': request.user.enseignant.tel
                           })


@transaction.atomic
def task_note_update(form, module_, groupe_, user):
    try:
        # if this is a POST request we need to process the form data
        liste_inscrits = Inscription.objects.filter(inscription_periodes__groupe=groupe_.id,
                                                    inscription_periodes__periodepgm=module_.periode).order_by(
            'etudiant__nom', 'etudiant__prenom')
        # liste_inscrits=Inscription.objects.filter(groupe=groupe_.id).order_by('etudiant__nom', 'etudiant__prenom')
        liste_evaluations = Evaluation.objects.filter(module=module_.id)
        module_suivi_ = get_object_or_404(ModulesSuivis, groupe=groupe_, module=module_)

        # process the data in form.cleaned_data as required
        data = form.cleaned_data
        for inscrit_ in liste_inscrits:
            resultat_ = get_object_or_404(Resultat, inscription=inscrit_, module=module_.id)
            if liste_evaluations.exists():
                for eval_ in liste_evaluations:
                    key_ = str(inscrit_.etudiant.matricule) + '_' + str(eval_.id)
                    note_, created = Note.objects.update_or_create(resultat=resultat_, evaluation=eval_, defaults={
                        'resultat': resultat_,
                        'evaluation': eval_,
                        'note': data[key_]
                    })
            else:
                # ce cas se pose quand on n'a que la moyenne générale du module
                key_ = str(inscrit_.etudiant.matricule) + '_moy'
                resultat_.moy = data[key_]
                resultat_.moy_post_delib = data[key_]
                resultat_.save(update_fields=['moy', 'moy_post_delib'])
        etat_saisie_ = data[str(groupe_.id) + '_' + str(module_.id)]
        if etat_saisie_ == True:
            module_suivi_.saisie_notes = 'T'
        else:
            module_suivi_.saisie_notes = 'C'
        module_suivi_.save()
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage(
                '[Talents] Erreur lors de l\'enregistrement des notes de' + str(module_) + ' du groupe ' + str(groupe_),
                'Bonjour,\n' +
                'Une erreur s\'est produite lors de l\'enregistrement des notes de ' + str(
                    module_) + ' du groupe ' + str(groupe_) + '\n' +
                'Demande de modification effectuée via le compte ' + user.email + '\n' +
                'Veuillez réessayer la saisie et l\'enregistrement \n' +
                'Bien cordialement.\n' +
                'Département', to=[user.email, module_.formation.programme.departement.responsable.user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)
    else:
        email = EmailMessage('[Talents] Confirmation de l\'enregistrement des notes de ' + str(
            module_.matiere.code) + ' du groupe ' + str(groupe_),
                             'Bonjour,\n' +
                             'L\'enregistrement des notes de ' + str(module_.matiere.code) + ' du groupe ' + str(
                                 groupe_) + ' a bien été effectué \n' +
                             'Modification effectuée via le compte ' + user.email + '\n' +
                             'Nous vous en remercions \n' +
                             'Bien cordialement.\n' +
                             'Département',
                             to=[user.email, module_.formation.programme.departement.responsable.user.email])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)


@login_required
def organisme_select_for_pfe_create(request):
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = SelectOrCreateOrganismeForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            data = form.cleaned_data

            # redirect to a new URL:
            return HttpResponseRedirect(reverse('pfe_create', kwargs={'organisme_pk': data['organisme'].sigle}))
        else:
            return render(request, 'scolar/import.html', {'form': form, 'titre': "Sélectionner ou créer un organisme"})
    # if a GET (or any other method) we'll create a blank form
    else:
        form = SelectOrCreateOrganismeForm()

        messages.info(request, "Merci de sélectionner un organisme d'accueil")
        messages.info(request, "Si l'organisme recherché n'existe pas, merci de le créer.")
        return render(request, 'scolar/import.html', {'form': form, 'titre': "Sélectionner ou créer un organisme"})


@login_required
def organisme_create_for_pfe_create(request):
    #     if request.user.is_etudiant():
    #         messages.error(request,"Vous n'avez pas les permissions pour executer cette opération.")
    #         return redirect('/accounts/login/?next=%s' % request.path)
    #
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = OrganismeForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            organisme = form.save()
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('pfe_create', kwargs={'organisme_pk': organisme.sigle}))
        else:
            return render(request, 'scolar/import.html', {'form': form, 'titre': "Créer un organisme"})
    # if a GET (or any other method) we'll create a blank form
    else:
        form = OrganismeForm()
        messages.info(request, "Merci d'utiliser ce formulaire pour créer un nouvel organisme d'accueil")
        return render(request, 'scolar/import.html', {'form': form, 'titre': "Créer un organisme"})


class OrganismeCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'scolar.add_organisme'
    model = Organisme
    fields = ['sigle', 'nom', 'adresse', 'pays', 'type', 'statut', 'nature', 'secteur', 'taille']
    template_name = 'scolar/create.html'
    success_message = "L'organisme a été créé avec succès!"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['pays'] = forms.ModelChoiceField(queryset=Pays.objects.all().order_by('nom'), initial='DZ',
                                                     required=True)
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('organisme_list')
        return form

    def get_context_data(self, **kwargs):
        context = super(OrganismeCreateView, self).get_context_data(**kwargs)
        titre = 'Créer un nouvel organisme partenaire'
        context['titre'] = titre
        return context


class OrganismeUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'scolar.change_organisme'
    model = Organisme
    fields = ['sigle', 'nom', 'adresse', 'pays', 'type', 'statut', 'nature', 'secteur', 'taille']
    template_name = 'scolar/update.html'
    success_message = "L'organisme a été modifié avec succès!"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['sigle'].widget.attrs['readonly'] = True
        form.fields['sigle'].required = False
        form.fields['pays'] = forms.ModelChoiceField(queryset=Pays.objects.all().order_by('nom'), initial='DZ',
                                                     required=True)
        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('organisme_list')
        return form


class OrganismeDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = Organisme
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_organisme'
    success_message = "L'organisme a bien été supprimé"

    def get_success_url(self):
        return reverse('organisme_list')


class OrganismeListView(TemplateView):
    template_name = 'scolar/filter_list.html'

    def get_context_data(self, **kwargs):
        context = super(OrganismeListView, self).get_context_data(**kwargs)

        filter_ = OrganismeFilter(self.request.GET, queryset=Organisme.objects.all().order_by('sigle'))

        filter_.form.helper = FormHelper()
        exclude_columns_ = exclude_columns(self.request.user)
        table = OrganismeTable(filter_.qs, exclude=exclude_columns_)
        RequestConfig(self.request).configure(table)

        context['filter'] = filter_
        context['table'] = table
        context['titre'] = 'Liste des organismes d\'accueil en stages'
        if self.request.user.is_staff_only():
            context['btn_list'] = {
                'Créer Organisme': reverse('organisme_create'),
                'Importer Organismes': reverse('organismes_import')
            }
        return context


class PFECreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UserPassesTestMixin, CreateView):
    permission_required = 'scolar.add_pfe'
    model = PFE
    fields = ['type', 'intitule', 'specialites', 'organisme', 'promoteur', 'email_promoteur', 'tel_promoteur',
              'coencadrants', 'reserve_pour', 'resume', 'bibliographie', 'objectifs', 'resultats_attendus',
              'antecedents', 'echeancier', 'moyens_informatiques', 'projet_recherche']
    template_name = 'scolar/create.html'
    success_message = "La proposition de PFE a bien été enregistrée. Elle sera soumise à un processus de validation."

    def test_func(self):
        if self.request.user.is_staff_only() or self.request.user.is_enseignant():
            return True
        elif self.request.user.is_etudiant():
            if self.request.user.etudiant.eligible_pfe():
                if self.request.user.etudiant.nb_depots_stages() >= 3:
                    messages.error(self.request,
                                   "Vous avez atteint le nombre maximum de dépôts de sujets de stage. Veuillez vous adresser au service des stages.")
                    return False
                else:
                    return True
            else:
                return False
        else:
            return False

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields[
            'type'].help_text = "PFE ou Master. Merci de soumettre deux sujets différents pour le PFE et Master."
        form.fields[
            'promoteur'].help_text = "Si le promoteur est enseignant à l'école, merci de le rajouter aux coencadrants aussi."
        form.fields[
            'antecedents'].help_text = "Renseignez les antécédents de ce stage en termes de travaux, produits, phases réaslisées, etc."
        form.fields[
            'echeancier'].help_text = "Mettre les différentes étapes en indiquant la durée en nombre de mois pour chacune. La durée totale doit être de 9 mois au moins pour un PFE."
        form.fields['organisme'] = forms.ModelChoiceField(
            queryset=Organisme.objects.all(),
            initial=self.kwargs.get("organisme_pk"),
            disabled=True,
            required=True,
        )
        form.fields[
            'specialites'].help_text = "Maintenez la touche Shift enfoncée pour sélectionner plusieurs spécialités."
        form.fields['coencadrants'] = forms.ModelMultipleChoiceField(
            queryset=Enseignant.objects.all().order_by('nom'),
            initial=self.request.user.enseignant if self.request.user.is_enseignant() else None,
            widget=ModelSelect2MultipleWidget(
                model=Enseignant,
                search_fields=['nom__icontains', 'prenom__icontains'],
            ),
            required=False,
            help_text="Sélection multiple possible. Tapez le nom ou prénom de l'enseignant ou deux espaces pour avoir la liste complète.",

        )
        form.fields['reserve_pour'] = forms.ModelMultipleChoiceField(
            queryset=Inscription.objects.filter(formation__programme__ordre__gte=4,
                                                formation__annee_univ__encours=True).order_by('etudiant__nom',
                                                                                              'etudiant__prenom'),
            widget=ModelSelect2MultipleWidget(
                model=Inscription,
                search_fields=['etudiant__nom__icontains', 'etudiant__prenom__icontains'],
            ),
            required=False,
            help_text="Sélection multiple possible. Tapez le nom ou prénom de l'étudiant",

        )

        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        if self.request.user.is_stage():
            self.success_url = reverse('service_pfe_list')
        elif self.request.user.is_enseignant():
            self.success_url = reverse('enseignant_pfe_list')
        elif self.request.user.is_etudiant():
            self.success_url = reverse('etudiant_pfe_list')
        else:
            self.success_url = reverse('home')
        return form

    def get_context_data(self, **kwargs):
        context = super(PFECreateView, self).get_context_data(**kwargs)
        titre = 'Proposer un nouveau PFE'
        context['titre'] = titre
        return context


@receiver(post_save, sender=PFE)
def notifier_pfe(sender, update_fields, instance, created, **kwargs):
    if created:
        email = EmailMessage("[Talents] Proposition d'un nouveau sujet de stage",
                             'Bonjour,\n' +
                             "Un nouveau sujet de stage a été soumis\n" +
                             "Vous pouvez lancer son processus de validation, via votre compte ou en suivant ce lien: \n\n" +
                             settings.PROTOCOLE_HOST + reverse('pfe_update', kwargs={'pk': instance.id}) + '\n\n' +
                             'Cordialement', to=settings.STAFF_EMAILS['stage'])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)

        # email au promoteur
        email = EmailMessage("[Talents] Proposition d'un nouveau sujet de stage N° " + str(instance.id),
                             'Bonjour,\n' +
                             "Un nouveau sujet de stage a été soumis\n\n" +

                             instance.intitule + "\n\n" +

                             "Il sera soumis à un processus de validation. Nous vous tiendrons informés de son statut de validation aussitôt terminée.\n" +
                             'Cordialement', to=[instance.email_promoteur])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)

        # email aux candidats potentiels
        email = EmailMessage("[Talents] Proposition d'un nouveau sujet de stage N° " + str(instance.id),
                             'Bonjour,\n' +
                             "Un nouveau sujet de stage a été soumis\n\n" +
                             instance.intitule + "\n\n" +
                             "Vous pouvez consulter la description détaillée ici:\n\n" +
                             settings.PROTOCOLE_HOST + reverse('pfe_detail', kwargs={'pk': instance.id}) + "\n" +
                             "Liste complète des sujets proposés:\n\n" +
                             settings.PROTOCOLE_HOST + reverse('pfe_list') + "\n" +
                             "Si un sujet vous intéresse, merci de contacter le promoteur\n" +
                             'Cordialement', to=settings.STAFF_EMAILS['futurs_stagiaires'])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)

    elif not instance.groupe:
        if instance.statut_validation == "RR":
            email = EmailMessage("[Talents] Votre sujet de stage N° " + str(instance.id) + " (Révision Requise)",
                                 'Bonjour,\n' +
                                 "Nous avons reçus les avis des collègues sur votre proposition de stage N° " + str(
                                     instance.id) + "\n" +
                                 "Intitulé: " + instance.intitule + "\n\n" +
                                 "Pourriez-vous apporter les améliorations nécessaires. Merci de renseigner le champs Réponse aux experts pour indiquer ce qui a été modifié.\n" +
                                 "N'oubliez pas de basculer le statut de validation du sujet vers 'Révision Terminée' après la modification\n" +
                                 "Vous pouvez modifier votre sujet en vous connectant à votre compte Talents ou via ce lien:\n\n" +
                                 settings.PROTOCOLE_HOST + reverse('pfe_update', kwargs={'pk': instance.id}) + '\n\n' +
                                 'Cordialement',
                                 to=settings.STAFF_EMAILS['stage'] + [coencadrant_.user.email for coencadrant_ in
                                                                      instance.coencadrants.all()] +
                                    [inscription_.etudiant.user.email for inscription_ in instance.reserve_pour.all()])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)

            email = EmailMessage("[Talents] Votre sujet de stage N° " + str(instance.id) + " (Révision Requise)",
                                 'Bonjour,\n' +
                                 "Nous avons reçus les avis des collègues sur votre proposition de stage N° " + str(
                                     instance.id) + "\n" +
                                 "Intitulé: " + instance.intitule + "\n\n" +
                                 "Vous pouvez visualiser le retour de la commission, dans le volet Validation, ici:\n\n" +
                                 settings.PROTOCOLE_HOST + reverse('pfe_detail', kwargs={'pk': instance.id}) + '\n\n' +
                                 "Merci d'indiquer aux co-encadrants de l'école ou à défaut à votre futur stagiaire, les modifications à apporter pour répondre aux recommendations de la commission.\n" +
                                 'Cordialement', to=[instance.email_promoteur])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)

        elif instance.statut_validation == "V" and instance.notification:
            # Supprimer les validations non renseignées
            email = EmailMessage("[Talents] Votre avis sur le sujet de stage N° " + str(instance.id),
                                 'Bonjour,\n' +
                                 "Nous avons reçus suffisemment d'avis sur la proposition de stage N° " + str(
                                     instance.id) + "\n\n" +
                                 "Intitulé: " + instance.intitule + "\n\n" +
                                 "Nous vous informons que votre avis n'est plus requis et le sujet a été validé\n" +
                                 "Nous vous remercions, et espérons vous solliciter pour d'autres avis.\n" +
                                 'Cordialement',
                                 to=settings.STAFF_EMAILS['stage'] + [validation_.expert.user.email for validation_ in
                                                                      instance.validations.filter(avis='X')])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)
            instance.validations.filter(avis='X').delete()

            email = EmailMessage("[Talents] Votre sujet de stage N° " + str(instance.id) + " (Validé)",
                                 'Bonjour,\n' +
                                 "Nous avons reçus les avis des collègues sur votre proposition de stage N° " + str(
                                     instance.id) + "\n\n" +
                                 "Intitulé: " + instance.intitule + "\n\n" +
                                 "Nous vous informons que votre sujet est maintenant validé\n" +
                                 'Cordialement',
                                 to=settings.STAFF_EMAILS['stage'] + [coencadrant_.user.email for coencadrant_ in
                                                                      instance.coencadrants.all()] +
                                    [inscription_.etudiant.user.email for inscription_ in
                                     instance.reserve_pour.all()] + [instance.email_promoteur])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)

            # marquer notification False pour qu'il y ait plus d'envoie de notification après de nouvelles mises à jours
            instance.notification = False
            instance.save()

        elif instance.statut_validation == "RT":
            email = EmailMessage("[Talents] Sujet de stage N° " + str(instance.id) + " (Révision Terminée)",
                                 'Bonjour,\n' +
                                 "La révision du sujet de stage N° " + str(instance.id) + " est terminée\n\n" +
                                 "Intitulé: " + instance.intitule + "\n\n" +
                                 "Vous pouvez procéder à son évaluation en vous connectant à votre compte ou via ce lien:\n\n" +
                                 settings.PROTOCOLE_HOST + reverse('pfe_update', kwargs={'pk': instance.id}) + '\n\n' +
                                 'Cordialement', to=settings.STAFF_EMAILS['stage'])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)

            email = EmailMessage("[Talents] Sujet de stage N° " + str(instance.id) + " (Révision Terminée)",
                                 'Bonjour,\n' +
                                 "Nous vous remercions d'avoir révisé le sujet de stage N° " + str(
                                     instance.id) + " \n\n" +
                                 "Intitulé: " + instance.intitule + "\n\n" +
                                 "Nous vous tiendrons informés de son statut de validation aussitôt terminée.\n" +
                                 'Cordialement',
                                 to=[coencadrant_.user.email for coencadrant_ in instance.coencadrants.all()] +
                                    [inscription_.etudiant.user.email for inscription_ in instance.reserve_pour.all()] +
                                    [instance.email_promoteur])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)
        elif instance.statut_validation == "LR":
            # identifier les experts qui ont déjà introduit leur avis favorable après révision
            experts_avec_avis_favorable = instance.validations.filter(avis='V').values_list('expert')
            # identifier les validations avec réserve pour leur demander de lever la réserve
            validations_avec_reserve = instance.validations.filter(Q(avis="SR") | Q(avis="MR") | Q(avis="N")).exclude(
                expert__in=experts_avec_avis_favorable)
            for validation_ in validations_avec_reserve:
                nouvelle_validation_, created = Validation.objects.get_or_create(pfe=instance.id,
                                                                                 expert=validation_.expert, avis="X",
                                                                                 defaults={
                                                                                     'pfe': instance,
                                                                                     'expert': validation_.expert,
                                                                                     'avis': 'X',
                                                                                     'debut': datetime.date.today()
                                                                                 })
                email = EmailMessage("[Talents] Levée de reserve sur le sujet de stage N° " + str(instance.id),
                                     'Bonjour,\n' +
                                     "Vous aviez émis une reserve sur la proposition de stage N° " + str(
                                         instance.id) + "\n\n" +
                                     "Intitulée: " + instance.intitule + "\n\n" +
                                     "Une version révisée a été soumise.\n" +
                                     "Nous vous invitons à réexaminer cette nouvelle version et réintroduire votre avis via votre compte Talents ou en suivant ce lien:\n\n" +
                                     settings.PROTOCOLE_HOST + reverse("validation_update",
                                                                       kwargs={'pk': nouvelle_validation_.id,
                                                                               'pfe_pk': instance.id}) + '\n\n' +
                                     'Cordialement', to=[nouvelle_validation_.expert.user.email])
                if settings.EMAIL_ENABLED:
                    email.send(fail_silently=True)


@receiver(m2m_changed, sender=PFE.coencadrants.through)
def notifier_coencadrants(sender, instance, action, pk_set, **kwargs):
    if action == "post_add" and not instance.groupe:
        coencadrant_list = []
        for enseignant_id_ in pk_set:
            enseignant_ = get_object_or_404(Enseignant, id=enseignant_id_)
            coencadrant_list.append(enseignant_)
        email = EmailMessage("[Talents] Proposition d'un nouveau sujet de stage N° " + str(instance.id),
                             'Bonjour,\n' +
                             "Un nouveau sujet de stage a été soumis\n\n" +

                             instance.intitule + "\n\n" +

                             "Il sera soumis à un processus de validation. Nous vous tiendrons informés de son statut de validation aussitôt terminée.\n" +
                             'Cordialement', to=[coencadrant_.user.email for coencadrant_ in coencadrant_list])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)


@receiver(m2m_changed, sender=PFE.reserve_pour.through)
def notifier_reserve_pour(sender, instance, action, pk_set, **kwargs):
    if action == "post_add" and not instance.groupe:
        reserve_pour_list = []
        for inscription_id_ in pk_set:
            inscription_ = get_object_or_404(Inscription, id=inscription_id_)
            reserve_pour_list.append(inscription_)
        email = EmailMessage("[Talents] Proposition d'un nouveau sujet de stage N° " + str(instance.id),
                             'Bonjour,\n' +
                             "Un nouveau sujet de stage a été soumis\n\n" +

                             instance.intitule + "\n\n" +

                             "Il sera soumis à un processus de validation. Nous vous tiendrons informés de son statut de validation aussitôt terminée.\n" +
                             'Cordialement',
                             to=[inscription_.etudiant.user.email for inscription_ in reserve_pour_list])
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)


class PFEUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UserPassesTestMixin, UpdateView):
    permission_required = 'scolar.change_pfe'
    model = PFE
    fields = ['statut_validation', 'type', 'intitule', 'specialites', 'organisme', 'promoteur', 'email_promoteur',
              'tel_promoteur', 'coencadrants', 'reserve_pour', 'resume', 'bibliographie', 'objectifs',
              'resultats_attendus', 'antecedents', 'echeancier', 'moyens_informatiques', 'projet_recherche',
              'reponse_aux_experts']
    template_name = 'scolar/pfe_update.html'
    success_message = "La proposition de sujet de stage a bien été enregistrée."

    def test_func(self):
        if not (
                self.request.user.is_staff_only() or self.request.user.is_enseignant() or self.request.user.is_etudiant()):
            return False
        else:
            pfe_ = get_object_or_404(PFE, id=self.kwargs.get("pk"))
            if self.request.user.is_direction() or self.request.user.is_stage():
                return True
            elif self.request.user.is_enseignant():
                if self.request.user.enseignant in pfe_.coencadrants.all():
                    return True
                else:
                    messages.error(self.request,
                                   "Vous ne vouvez pas modifier ce sujet car vous ne figurez pas parmi les co-encadrants.")
                    return False
            elif self.request.user.is_etudiant():
                allow = False
                etudiant_list = []
                for inscription_ in pfe_.reserve_pour.all():
                    etudiant_list.append(inscription_.etudiant.matricule)
                if self.request.user.etudiant.matricule in etudiant_list and pfe_.statut_validation in ['S', 'RR', 'N']:
                    allow = True
                return allow
            else:
                return False

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        pfe_ = get_object_or_404(PFE, id=self.kwargs.get("pk"))
        form.fields[
            'statut_validation'].help_text = "Sélectionnez Révision Terminée pour signaler la fin de la révision."
        form.fields[
            'specialites'].help_text = "Maintenez la touche Shift enfoncée pour sélectionner plusieurs spécialités."
        form.fields['coencadrants'] = forms.ModelMultipleChoiceField(
            queryset=Enseignant.objects.all().order_by('nom'),
            initial=pfe_.coencadrants.all(),
            widget=ModelSelect2MultipleWidget(
                model=Enseignant,
                search_fields=['nom__icontains', 'prenom__icontains'],
            ),
            required=False,
            help_text="Sélection multiple possible. Tapez le nom ou prénom de l'enseignant ou deux espaces pour avoir la liste complète.",

        )
        form.fields['reserve_pour'] = forms.ModelMultipleChoiceField(
            queryset=Inscription.objects.filter(formation__programme__ordre__gte=4).order_by('etudiant__nom',
                                                                                             'etudiant__prenom'),
            initial=pfe_.reserve_pour.all(),
            widget=ModelSelect2MultipleWidget(
                model=Inscription,
                search_fields=['etudiant__nom__icontains', 'etudiant__prenom__icontains'],
            ),
            required=False,
            help_text="Sélection multiple possible. Tapez le nom ou prénom de l'étudiant",

        )

        if self.request.user.is_stage() or self.request.user.is_direction():
            form.fields['statut_validation'] = forms.ChoiceField(disabled=False, choices=STATUT_VALIDATION,
                                                                 initial=pfe_.statut_validation)
            form.fields['reponse_aux_experts'].disabled = True
        elif pfe_.statut_validation == "RR":
            form.fields['statut_validation'] = forms.ChoiceField(disabled=False, choices=(
            ('RT', 'Révision Terminée'), ('RR', 'Révision Requise')), initial=pfe_.statut_validation)
            form.fields['reponse_aux_experts'].disabled = False
            form.fields[
                'reponse_aux_experts'].help_text = "Utiliser ce champs pour répondre aux experts et indiquer précisemment les modifications apportées"
        elif pfe_.statut_validation == 'V':
            for key_ in form.fields.keys():
                form.fields[key_].widget.attrs['readonly'] = True
            if not pfe_.groupe:
                form.fields['reserve_pour'].widget.attrs['readonly'] = False
        else:
            form.fields['statut_validation'] = forms.ChoiceField(disabled=True, choices=STATUT_VALIDATION,
                                                                 initial=pfe_.statut_validation)

        form.helper.add_input(Submit('submit', 'Modifier', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        if self.request.user.is_stage():
            self.success_url = reverse('service_pfe_list')
            form.helper.add_input(Button('modifier', 'Retour à la liste', css_class='btn-info',
                                         onclick="window.location.href='" + reverse('service_pfe_list') + "'"))
        elif self.request.user.is_etudiant():
            self.success_url = reverse('etudiant_pfe_list')
            form.helper.add_input(Button('modifier', 'Retour à la liste', css_class='btn-info',
                                         onclick="window.location.href='" + reverse('etudiant_pfe_list') + "'"))
        elif self.request.user.is_enseignant():
            self.success_url = reverse('enseignant_pfe_list')
            form.helper.add_input(Button('modifier', 'Retour à la liste', css_class='btn-info',
                                         onclick="window.location.href='" + reverse('enseignant_pfe_list') + "'"))
        else:
            self.success_url = reverse('home')
        return form

    def get_context_data(self, **kwargs):
        context = super(PFEUpdateView, self).get_context_data(**kwargs)
        titre = "Gérer la soumission d'un sujet de stage"
        context['titre'] = titre
        exclude_columns_ = exclude_columns(self.request.user)
        if (not self.request.user.is_stage()):
            exclude_columns_.append('expert')
        if self.request.user.is_etudiant():
            exclude_columns_.append('action')

        table = ValidationTable(Validation.objects.filter(pfe=self.kwargs.get("pk")), exclude=exclude_columns_)
        RequestConfig(self.request).configure(table)
        context['pfe_validation_table'] = table

        return context


class PFEDetailView(TemplateView):
    template_name = 'scolar/pfe_detail.html'

    def get_context_data(self, **kwargs):
        context = super(PFEDetailView, self).get_context_data(**kwargs)
        titre = 'Sujet de Stage N°: ' + self.kwargs.get("pk")
        context['titre'] = titre
        pfe_ = get_object_or_404(PFE, id=self.kwargs.get("pk"))
        context['pfe_form'] = PFEDetailForm(instance=pfe_)

        exclude_columns_ = exclude_columns(self.request.user)
        if not self.request.user.is_authenticated:
            exclude_columns_.append('expert')
            exclude_columns_.append('action')
        else:
            if (not self.request.user.is_stage()):
                exclude_columns_.append('expert')
            if self.request.user.is_etudiant():
                exclude_columns_.append('action')

        table = ValidationTable(Validation.objects.filter(pfe=self.kwargs.get("pk")), exclude=exclude_columns_)
        RequestConfig(self.request).configure(table)
        context['pfe_validation_table'] = table

        return context


class PFEPDFView(PDFTemplateView):
    template_name = 'scolar/pfe_fiche_pdf.html'
    cmd_options = {
        'orientation': 'Portrait',
        'page-size': 'A4',
    }

    def get_context_data(self, **kwargs):
        context = super(PFEPDFView, self).get_context_data(**kwargs)
        pfe_ = get_object_or_404(PFE, id=self.kwargs.get('pfe_pk'))
        self.filename = 'FICHE_PFE_' + str(pfe_.id) + '.pdf'

        context['pfe'] = pfe_
        context['moyens_informatiques'] = dict(OPTION_MOYENS)
        context['avis_expert'] = dict(OPTIONS_VALIDATION)
        return context


class ExpertsIndexView(LoginRequiredMixin, UserPassesTestMixin, PDFTemplateView):
    template_name = 'scolar/experts_index_pdf.html'

    def test_func(self):
        return self.request.user.is_stage() or self.request.user.is_direction() or self.request.user.is_top_management()

    def get_context_data(self, **kwargs):
        context = super(ExpertsIndexView, self).get_context_data(**kwargs)

        experts_index = {}
        for enseignant_ in Enseignant.objects.all().order_by('nom', 'prenom'):
            expertise_list = Validation.objects.filter(expert=enseignant_, avis__isnull=False,
                                                       pfe__groupe__section__formation__annee_univ__encours=True).order_by(
                'pfe')
            if expertise_list.exists():
                experts_index[enseignant_] = []
                for expertise_ in expertise_list:
                    if not expertise_.pfe in experts_index[enseignant_]:
                        experts_index[enseignant_].append(expertise_.pfe)

        context['experts_index'] = experts_index
        context['titre'] = "Index des experts des sujets de PFE"
        context['annee_univ'] = AnneeUniv.objects.get(encours=True)
        return context


@login_required
def pfe_fiche_list_pdf_view(request, formation_pk, periode_pk):
    if not request.user.is_stage():
        messages.error(request, "Vous n'avez pas la permission d'exécution de cette opération")
        return redirect('/accounts/login/?next=%s' % request.path)
    try:
        t = threading.Thread(target=task_pfe_fiche_list_pdf, args=[formation_pk, request.user])
        t.setDaemon(True)
        t.start()
        messages.success(request, "Votre demande de génération des fiches PFE est effectuée avec succès.")
        messages.success(request, "Une notification vous sera transmise une fois la tâche terminée.")

    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request,
                           "ERREUR: lors de la demande de génération des fiches PFE. Merci de le signaler à l'administrateur.")
    return HttpResponseRedirect(reverse('document_list'))


def task_pfe_fiche_list_pdf(formation_pk, user):
    try:
        context = {}
        cmd_options = {
            'orientation': 'Portrait',
            'page-size': 'A4',
        }

        formation_ = Formation.objects.get(id=formation_pk)
        pfe_list = PFE.objects.filter(groupe__section__formation=formation_).order_by('id')
        filename = 'FICHES_PFE_' + str(formation_) + '.pdf'
        context['pfe_list'] = pfe_list
        context['date'] = datetime.date.today()
        context['institution'] = user.institution()
        context['moyens_informatiques'] = dict(OPTION_MOYENS)
        context['avis_expert'] = dict(OPTIONS_VALIDATION)

        pdf_ = render_pdf_from_template(input_template='scolar/pfe_fiche_list_pdf.html',
                                        header_template=None,
                                        footer_template=None,
                                        context=context,
                                        cmd_options=cmd_options)
        email = EmailMessage('[Talents] Génération des Fiches PFE de ' + str(formation_),
                             'Bonjour,\n' +
                             'La génération des fiches PFE de ' + str(formation_) + ' est terminée \n' +
                             'Veuillez trouver ci-jointes les fiches\n' +
                             'Bien cordialement.\n' +
                             'Département', to=[user.email]
                             )
        email.attach(filename, pdf_, 'application/pdf')
        if settings.EMAIL_ENABLED:
            email.send(fail_silently=True)
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            email = EmailMessage(
                '[Talents] Erreur lors de la génération des fiches PFE de  la formation ' + str(formation_),
                'Bonjour,\n' +
                'Une erreur s\'est produite lors de la génération des fiches PFE de la formation ' + str(
                    formation_) + '\n' +
                'Bien cordialement.\n' +
                'Département', to=[user.email])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)


class PFEDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = PFE
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_pfe'
    success_message = "La proposition du stage a bien été supprimée"

    def get_success_url(self):
        return reverse('service_pfe_list')


class PFEListView(TemplateView):
    template_name = 'scolar/filter_list.html'

    def get_context_data(self, **kwargs):
        context = super(PFEListView, self).get_context_data(**kwargs)

        # filter_ = PFEFilter(self.request.GET, queryset=PFE.objects.filter(groupe__isnull=True).order_by('id'))
        filter_ = PFEFilter(self.request.GET,
                            queryset=PFE.objects.all().order_by('-groupe__section__formation__annee_univ__annee_univ'))
        filter_.form.helper = FormHelper()
        exclude_columns_ = exclude_columns(self.request.user)
        if not self.request.user.is_authenticated:
            exclude_columns_.append('expert')
        elif not self.request.user.is_staff_only():
            exclude_columns_.append('expert')
        table = PFETable(filter_.qs, exclude=exclude_columns_)
        RequestConfig(self.request).configure(table)

        context['filter'] = filter_
        context['table'] = table
        context['titre'] = 'Liste des sujets de stages proposés'
        if self.request.user.is_authenticated:
            if self.request.user.is_staff_only():
                context['btn_list'] = {
                    'Nouveau Sujet': reverse('organisme_select_for_pfe_create'),
                    'Import PFE': reverse('import_affectation_pfe'),
                    'Confirmer Attribution PFE': reverse('import_affectation_pfe_valide')
                }
        return context


class ServicePFEListView(LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/service_pfe_list.html'
    permission_required = 'scolar.view_pfe'

    def test_func(self):
        return self.request.user.is_stage() or self.request.user.is_direction()

    def get_context_data(self, **kwargs):
        context = super(ServicePFEListView, self).get_context_data(**kwargs)

        pfe_soumis_table = PFETable(
            PFE.objects.filter(Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
                               statut_validation='S').order_by('id'))
        pfe_soumis_nb = PFE.objects.filter(
            Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
            statut_validation='S').count()

        pfe_attente_validation_table = PFETable(
            PFE.objects.filter(Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
                               statut_validation='W').order_by('id'))
        pfe_attente_validation_nb = PFE.objects.filter(
            Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
            statut_validation='W').count()

        pfe_revision_requise_table = PFETable(
            PFE.objects.filter(Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
                               statut_validation='RR').order_by('id'))
        pfe_revision_requise_nb = PFE.objects.filter(
            Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
            statut_validation='RR').count()

        pfe_revision_terminee_table = PFETable(
            PFE.objects.filter(Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
                               statut_validation='RT').order_by('id'))
        pfe_revision_terminee_nb = PFE.objects.filter(
            Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
            statut_validation='RT').count()

        pfe_levee_reserve_table = PFETable(
            PFE.objects.filter(Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
                               statut_validation='LR').order_by('id'))
        pfe_levee_reserve_nb = PFE.objects.filter(
            Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
            statut_validation='LR').count()

        pfe_valide_attribue_table = PFETable(
            PFE.objects.filter(Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
                               statut_validation='V', reserve_pour__isnull=False).distinct().order_by('id'))
        pfe_valide_attribue_nb = PFE.objects.filter(
            Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True), statut_validation='V',
            reserve_pour__isnull=False).distinct().count()

        pfe_valide_non_attribue_table = PFETable(
            PFE.objects.filter(Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
                               statut_validation='V', reserve_pour__isnull=True).distinct().order_by('id'))
        pfe_valide_non_attribue_nb = PFE.objects.filter(
            Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True), statut_validation='V',
            reserve_pour__isnull=True).distinct().count()

        pfe_non_valide_table = PFETable(
            PFE.objects.filter(Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
                               statut_validation='N').order_by('id'))
        pfe_non_valide_nb = PFE.objects.filter(
            Q(groupe__isnull=True) | Q(groupe__section__formation__annee_univ__encours=True),
            statut_validation='N').count()

        RequestConfig(self.request).configure(pfe_soumis_table)

        context['pfe_soumis_table'] = pfe_soumis_table
        context['pfe_soumis_nb'] = pfe_soumis_nb

        context['pfe_attente_validation_table'] = pfe_attente_validation_table
        context['pfe_attente_validation_nb'] = pfe_attente_validation_nb

        context['pfe_revision_requise_table'] = pfe_revision_requise_table
        context['pfe_revision_requise_nb'] = pfe_revision_requise_nb

        context['pfe_revision_terminee_table'] = pfe_revision_terminee_table
        context['pfe_revision_terminee_nb'] = pfe_revision_terminee_nb

        context['pfe_levee_reserve_table'] = pfe_levee_reserve_table
        context['pfe_levee_reserve_nb'] = pfe_levee_reserve_nb

        context['pfe_valide_attribue_table'] = pfe_valide_attribue_table
        context['pfe_valide_attribue_nb'] = pfe_valide_attribue_nb

        context['pfe_valide_non_attribue_table'] = pfe_valide_non_attribue_table
        context['pfe_valide_non_attribue_nb'] = pfe_valide_non_attribue_nb

        context['pfe_non_valide_table'] = pfe_non_valide_table
        context['pfe_non_valide_nb'] = pfe_non_valide_nb

        context['titre'] = 'Validation des sujets de stages'
        return context


class EnseignantPFEListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/list.html'

    def test_func(self):
        return self.request.user.is_enseignant()

    def get_context_data(self, **kwargs):
        context = super(EnseignantPFEListView, self).get_context_data(**kwargs)

        pfe_table = PFETable(
            PFE.objects.filter(groupe__isnull=True, coencadrants__in=[self.request.user.enseignant]).order_by('id'),
            exclude=exclude_columns(self.request.user))
        context['table'] = pfe_table
        context['titre'] = "Mes sujets de stages"
        context['btn_list'] = {
            'Nouveau Sujet': reverse('organisme_select_for_pfe_create')
        }
        return context


class EtudiantPFEListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/list.html'

    def test_func(self):
        return self.request.user.is_etudiant()

    def get_context_data(self, **kwargs):
        context = super(EtudiantPFEListView, self).get_context_data(**kwargs)

        pfe_table = PFETable(
            PFE.objects.filter(groupe__isnull=True, reserve_pour__etudiant__in=[self.request.user.etudiant]).order_by(
                'id'), exclude=exclude_columns(self.request.user))
        context['table'] = pfe_table
        context['titre'] = "Mes sujets de stages"
        context['btn_list'] = {
            'Nouveau Sujet': reverse('organisme_select_for_pfe_create')
        }
        return context


class EnseignantExpertisePFEListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scolar/list.html'

    def test_func(self):
        return self.request.user.is_enseignant()

    def get_context_data(self, **kwargs):
        context = super(EnseignantExpertisePFEListView, self).get_context_data(**kwargs)
        exclude_columns_ = exclude_columns(self.request.user)
        #         if (not self.request.user.is_staff_only()):
        #             exclude_columns_.append('expert')

        validation_table = ValidationTable(
            Validation.objects.filter(pfe__groupe__isnull=True, expert=self.request.user.enseignant),
            exclude=exclude_columns_)
        context['table'] = validation_table
        context['titre'] = "Sujets de stages à expertiser"
        return context


@login_required
def commission_validation_create_view(request, pfe_pk):
    if not (request.user.is_stage() or request.user.is_direction()):
        messages.error(request, "Vous n'avez pas les permissions pour executer cette opération.")
        return redirect('/accounts/login/?next=%s' % request.path)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = CommissionValidationCreateForm(pfe_pk, request.POST)
        # check whether it's valid:
        if form.is_valid():
            data = form.cleaned_data
            try:
                pfe_ = get_object_or_404(PFE, id=pfe_pk)
                experts_list = []
                for expert_id_ in data['experts']:
                    expert_ = get_object_or_404(Enseignant, id=expert_id_)
                    experts_list.append(expert_)
                for expert_ in experts_list:
                    validation_, created = Validation.objects.get_or_create(pfe=pfe_, expert=expert_.id, defaults={
                        'pfe': pfe_,
                        'expert': expert_,
                        'debut': datetime.date.today(),
                        'fin': data['fin']
                    })
                pfe_.statut_validation = 'W'
                pfe_.save(update_fields=['statut_validation'])

                if request.is_secure():
                    action_url = "https"
                else:
                    action_url = "http"
                action_url += "://" + request.get_host() + reverse('enseignant_expertise_pfe_list')
                email = EmailMessage("[Talents] Validation du sujet de stage N° " + pfe_pk,
                                     'Bonjour,\n' +
                                     "Un nouveau sujet de stage a été soumis.\n\n" +

                                     "Intitulé: " + pfe_.intitule + "\n\n" +

                                     "Nous vous invitons à donner votre avis sur ce sujet au plus tard le: " + data[
                                         'fin'].strftime("%d/%m/%Y") + "\n"
                                                                       "Vous trouverez ce sujet dans votre compte Talents/Stages/Mes Validations, ou vous pouvez procéder à sa validation en cliquant ici:\n" +
                                     action_url + ' ,\n' +
                                     'Cordialement',
                                     to=settings.STAFF_EMAILS['stage'] + [expert_.user.email for expert_ in
                                                                          experts_list])
                if settings.EMAIL_ENABLED:
                    email.send(fail_silently=True)
            except Exception:
                if settings.DEBUG:
                    raise Exception("Création commission validation.")
                else:
                    messages.error(request,
                                   "Une erreur s'est produite pendant la création de la commission de Validation. Si le problème persiste, merci de le signaler à l'administrateur.")
                    render(request, 'scolar/import.html',
                           {'form': form, 'titre': "Création d'une commission de validation"})
            messages.success(request,
                             "La commission de validation a été créée avec succès. Une notification a été envoyée aux membres de la commission.")
            # redirect to a new URL:
            return HttpResponseRedirect(reverse('pfe_update', kwargs={'pk': pfe_.id}))
        else:
            return render(request, 'scolar/import.html',
                          {'form': form, 'titre': "Création d'une commission de validation"})
    # if a GET (or any other method) we'll create a blank form
    else:
        form = CommissionValidationCreateForm(pfe_pk)
        messages.info(request, "Merci d'utiliser ce formulaire pour créer une commission de validation")
        return render(request, 'scolar/import.html', {'form': form, 'titre': "Création d'une commission de validation"})


class ValidationCreateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'scolar.add_validation'
    model = Validation
    fields = ['pfe', 'expert', 'debut']
    template_name = 'scolar/create.html'
    success_message = "Un(e) membre de la commission de validation a été ajouté(e) avec succès."

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()
        form.fields['pfe'] = forms.ModelChoiceField(disabled=True, queryset=PFE.objects.all(),
                                                    initial=self.kwargs.get("pfe_pk"))
        form.fields['debut'] = forms.DateField(disabled=True, input_formats=settings.DATE_INPUT_FORMATS,
                                               widget=DatePickerInput(format='%d/%m/%Y'), initial=datetime.date.today())
        form.helper.add_input(Submit('submit', 'Ajouter', css_class='btn-primary'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary', onclick="window.history.back()"))
        self.success_url = reverse('pfe_update', kwargs={'pk': self.kwargs.get("pfe_pk")})
        return form

    def get_context_data(self, **kwargs):
        context = super(ValidationCreateView, self).get_context_data(**kwargs)
        titre = 'Ajouter un(e) membre à la commission de validation'
        context['titre'] = titre
        return context


class ValidationUpdateView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, UserPassesTestMixin,
                           UpdateView):
    permission_required = 'scolar.change_validation'
    model = Validation
    fields = ['avis', 'commentaire', 'fin']
    template_name = 'scolar/validation_update.html'
    success_message = "Une évaluation d'un stage a été introduite avec succès."

    def test_func(self):
        pfe_ = get_object_or_404(PFE, id=self.kwargs.get("pfe_pk"))
        validation_ = get_object_or_404(Validation, id=self.kwargs.get("pk"))
        if not pfe_.statut_validation in ['V', 'N'] and validation_.avis == 'X':
            return True
        else:
            messages.warning(self.request, "Le nouveau statut du sujet N° " + str(pfe_.id) + " est : " +
                             str(dict(STATUT_VALIDATION)[pfe_.statut_validation]) +
                             ". Vous ne pouvez pas introduire votre avis. Merci.")
            return False

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.helper = FormHelper()

        form.fields['commentaire'].label = "Si réserves ou avis défavorable, alors expliquez ici"

        form.fields['fin'] = forms.DateField(label="Fait le", input_formats=settings.DATE_INPUT_FORMATS,
                                             widget=DatePickerInput(format='%d/%m/%Y'), initial=datetime.date.today())

        form.helper.add_input(Submit('submit', 'Enregistrer', css_class='btn-warning'))
        form.helper.add_input(Button('cancel', 'Annuler', css_class='btn-secondary',
                                     onclick="window.location.href='" + reverse('enseignant_expertise_pfe_list') + "'"))
        self.success_url = reverse('enseignant_expertise_pfe_list')
        return form

    def get_context_data(self, **kwargs):
        context = super(ValidationUpdateView, self).get_context_data(**kwargs)
        titre = 'Validation du sujet N°: ' + self.kwargs.get("pfe_pk")
        context['titre'] = titre
        pfe_ = get_object_or_404(PFE, id=self.kwargs.get("pfe_pk"))
        context['pfe_form'] = PFEDetailForm(instance=pfe_)
        exclude_columns_ = exclude_columns(self.request.user)
        exclude_columns_.append('action')
        validation_table = ValidationTable(
            Validation.objects.filter(pfe=pfe_.id, expert=self.request.user.enseignant).exclude(avis='X'),
            exclude=exclude_columns_)
        context['validation_table'] = validation_table

        return context


@receiver(post_save, sender=Validation)
def notifier_validation(sender, update_fields, instance, created, **kwargs):
    if instance.pfe:
        if instance.pfe.statut_validation == 'W' and instance.pfe.nb_avis() == 3:
            email = EmailMessage("[Talents] 3 Avis collectés sur le sujet N° " + str(instance.pfe.id),
                                 'Bonjour,\n' +
                                 "Le sujet de stage N° " + str(instance.pfe.id) + " a reçu au moins 3 avis.\n" +
                                 "Vous pouvez statuer sur sa validation.\n\n" +
                                 settings.PROTOCOLE_HOST + reverse('pfe_update',
                                                                   kwargs={'pk': instance.pfe.id}) + '\n\n' +
                                 'Cordialement', to=settings.STAFF_EMAILS['stage'])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)
        elif instance.pfe.statut_validation == 'LR' and instance.avis == 'V':
            email = EmailMessage("[Talents] Une levée de réserve sur le sujet N° " + str(instance.pfe.id),
                                 'Bonjour,\n' +
                                 "Le sujet de stage N° " + str(instance.pfe.id) + " a reçu une levée de réserve.\n" +
                                 "Vous pouvez statuer sur sa validation.\n\n" +
                                 settings.PROTOCOLE_HOST + reverse('pfe_update',
                                                                   kwargs={'pk': instance.pfe.id}) + '\n\n' +
                                 'Cordialement', to=settings.STAFF_EMAILS['stage'])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)
        elif instance.pfe.statut_validation == 'LR' and (instance.avis == 'SR' or instance.avis == 'MR'):
            email = EmailMessage("[Talents] Une nouvelle réserve sur le sujet N° " + str(instance.pfe.id),
                                 'Bonjour,\n' +
                                 "Le sujet de stage N° " + str(instance.pfe.id) + " a reçu une nouvelle réserve.\n" +
                                 "Vous pouvez statuer sur sa validation.\n\n" +
                                 settings.PROTOCOLE_HOST + reverse('pfe_update',
                                                                   kwargs={'pk': instance.pfe.id}) + '\n\n' +
                                 'Cordialement', to=settings.STAFF_EMAILS['stage'])
            if settings.EMAIL_ENABLED:
                email.send(fail_silently=True)


class ValidationDeleteView(LoginRequiredMixin, SuccessMessageMixin, PermissionRequiredMixin, DeleteView):
    model = Validation
    template_name = 'scolar/delete.html'
    permission_required = 'scolar.delete_validation'
    success_message = "L'expertise du stage a bien été supprimée"

    def get_success_url(self):
        return reverse('pfe_update', kwargs={'pk': self.kwargs.get('pfe_pk')})


@login_required
def note_pfe_update(request, module_pk, groupe_pk):
    # Il faudra refaire le traitement des données du formuliare pour n'enregistrer
    # que les données ayant changé et pas toutes (form.changed_data) pour éviter des
    # problèmes de performance
    module_ = get_object_or_404(Module, id=module_pk)
    groupe_ = get_object_or_404(Groupe, id=groupe_pk)
    module_suivi_ = get_object_or_404(ModulesSuivis, groupe=groupe_, module=module_)

    if request.user.is_etudiant():
        messages.error(request, "Vous n'avez pas les permissions d'accès à cette opération")
        return redirect('/accounts/login/?next=%s' % request.path)

    elif request.user.is_direction() or request.user.is_stage():
        pass
    elif request.user.is_enseignant():
        if not assure_module_groupe(request.user.enseignant, module_, groupe_):
            messages.error(request, "Vous n'avez pas les permissions d'accès à cette opération")
            return redirect('/accounts/login/?next=%s' % request.path)
        elif module_suivi_.saisie_notes == 'T':
            messages.error(request,
                           "La version finale de l'évaluation avait été établie. Il n'est plus possible de modifier cette évaluation")
            return HttpResponseRedirect(
                reverse('note_list', kwargs={'groupe_pk': groupe_pk, 'matiere_pk': module_.matiere.id}))

    # if this is a POST request we need to process the form data
    # liste_inscrits=Inscription.objects.filter(groupe=groupe_pk)
    liste_inscrits = Inscription.objects.filter(inscription_periodes__groupe=groupe_.id,
                                                inscription_periodes__periodepgm__periode=module_.periode.periode).order_by(
        'etudiant__nom', 'etudiant__prenom')
    liste_evaluations = Evaluation.objects.filter(module=module_pk)

    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = NotesPFEUpdateForm(groupe_pk, module_pk, request, request.POST)
        # check whether it's valid:
        if form.is_valid():

            if module_.formation.archive:
                messages.error(request, "La saisie des notes est clôturée pour cette formation.")
            else:
                try:
                    # process the data in form.cleaned_data as required
                    data = form.cleaned_data
                    for inscrit_ in liste_inscrits:
                        resultat_ = get_object_or_404(Resultat, inscription=inscrit_, module__matiere=module_.matiere)
                        for eval_ in liste_evaluations:
                            note_ = get_object_or_404(Note, resultat=resultat_, evaluation=eval_)
                            key_ = str(inscrit_.etudiant.matricule) + "_" + str(eval_.id)
                            note_.note = data[key_]
                            note_.save()
                            for competence_ in eval_.competence_elements.all():
                                if competence_.commune_au_groupe:
                                    key_ = str(groupe_.code) + "_" + str(
                                        eval_.id) + '_' + competence_.competence_element.code
                                else:
                                    key_ = str(inscrit_.etudiant.matricule) + "_" + str(
                                        eval_.id) + '_' + competence_.competence_element.code
                                NoteCompetenceElement.objects.update_or_create(
                                    evaluation_competence_element=competence_, note_globale=note_, defaults={
                                        'evaluation_competence_element': competence_,
                                        'note_globale': note_,
                                        'valeur': data[key_]
                                    })

                        key_ = str(inscrit_.etudiant.matricule) + "_mention"
                        inscrit_.mention = data[key_]

                        key_ = str(inscrit_.etudiant.matricule) + "_moy"
                        resultat_.moy = data[key_]
                        resultat_.moy_post_delib = data[key_]
                        resultat_.save(update_fields=['moy', 'moy_post_delib'])

                        inscrit_.moy = inscrit_.moyenne()
                        if inscrit_.moy >= 10:
                            inscrit_.decision_jury = 'A'
                        else:
                            inscrit_.decision_jury = 'N'
                        inscrit_.save(update_fields=['mention', 'moy', 'decision_jury'])

                    etat_saisie_ = data[str(groupe_.id) + '_' + str(module_.id)]
                    if etat_saisie_ == True:
                        module_suivi_.saisie_notes = 'T'
                    else:
                        module_suivi_.saisie_notes = 'C'
                    module_suivi_.save()

                    soutenance_ = get_object_or_404(Soutenance, id=groupe_.soutenance.id)
                    pfe_ = get_object_or_404(PFE, id=groupe_.pfe.id)
                    soutenance_.depot_biblio = data[str(soutenance_.id) + '_depot_biblio']
                    soutenance_.save()

                    if soutenance_.date == datetime.date.today():
                        # Envoyer une notification au service des stages

                        if request.is_secure():
                            action_url = "https"
                        else:
                            action_url = "http"
                        action_url += "://" + request.get_host() + reverse('pv_pfe_pdf', kwargs={'groupe_pk': groupe_pk,
                                                                                                 'module_pk': module_pk})

                        email = EmailMessage('[Talents] Délibérations Terminées ' + groupe_.code,
                                             'Bonjour,\n' +
                                             'Les délibérations de la soutenance du stage N° ' + groupe_.code + ' sont terminées\n' +
                                             'Vous pouvez imprimer le PV pour la signature en cliquant sur ce lien: \n\n' +
                                             action_url + ' \n'
                                                          'Bien cordialement.\n'
                                             , to=settings.STAFF_EMAILS['stage'])
                        if settings.EMAIL_ENABLED:
                            email.send(fail_silently=True)

                    if request.user.is_stage():
                        pfe_.coencadrants.clear()
                        for enseignant_id in data[str(pfe_.id) + '_coencadrants']:
                            enseignant_ = Enseignant.objects.get(id=enseignant_id)
                            pfe_.coencadrants.add(enseignant_)
                        pfe_.promoteur = data[str(pfe_.id) + '_promoteur']
                        pfe_.intitule = data[str(pfe_.id) + '_intitule']
                        pfe_.save()

                        soutenance_.president = data[str(soutenance_.id) + '_president']
                        soutenance_.rapporteur = data[str(soutenance_.id) + '_rapporteur']
                        soutenance_.examinateur = data[str(soutenance_.id) + '_examinateur']
                        soutenance_.coencadrant = data[str(soutenance_.id) + '_coencadrant']
                        soutenance_.assesseur1 = data[str(soutenance_.id) + '_assesseur1']
                        soutenance_.assesseur2 = data[str(soutenance_.id) + '_assesseur2']

                        soutenance_.invite1 = data[str(soutenance_.id) + '_invite1']
                        soutenance_.invite2 = data[str(soutenance_.id) + '_invite2']
                        soutenance_.date = data[str(soutenance_.id) + '_date']
                        soutenance_.depot_biblio = data[str(soutenance_.id) + '_depot_biblio']
                        soutenance_.save()

                        # TODO il faut modifier ce qui suit. Il faut déterminer le type de l'activité directement à partir de l'activité (FK vers une table des type de charges
                        if module_.formation.programme.ordre == 5:
                            type_ = 'PFE_Enc'
                            charge_ = ActiviteChargeConfig.objects.get(type=type_).vh_eq_td
                        else:
                            type_ = 'Mem_Enc'
                            charge_ = ActiviteChargeConfig.objects.get(type=type_).vh_eq_td
                        # Mettre à jour les charges en fonction de la saisie du jury
                        activite_encadrement, created = Activite.objects.get_or_create(module=module_pk,
                                                                                       cible__in=[groupe_pk, ],
                                                                                       type=type_, defaults={
                                'type': type_,
                                'module': module_,
                                'vh': charge_,  # TODO mettre les type de charge et VH associé dans une table
                                'repeter_chaque_semaine': False,
                                'repartir_entre_intervenants': True,
                            })
                        activite_encadrement.cible.clear()
                        activite_encadrement.cible.add(groupe_)
                        for enseignant_ in activite_encadrement.assuree_par.all():
                            activite_encadrement.assuree_par.remove(enseignant_)
                        for enseignant in pfe_.coencadrants.all():
                            activite_encadrement.assuree_par.add(enseignant)
                        activite_encadrement.save()

                        # TODO il faut modifier ce qui suit. Il faut déterminer le type de l'activité directement à partir de l'activité (FK vers une table des type de charges
                        if module_.formation.programme.ordre == 5:
                            type_ = 'PFE_Sout'
                            charge_ = ActiviteChargeConfig.objects.get(type=type_).vh_eq_td
                        else:
                            type_ = 'Mem_Sout'
                            charge_ = ActiviteChargeConfig.objects.get(type=type_).vh_eq_td

                        activite_soutenance, created = Activite.objects.get_or_create(module=module_pk,
                                                                                      cible__in=[groupe_pk, ],
                                                                                      type=type_, defaults={
                                'type': type_,
                                'module': module_,
                                'vh': charge_,  # TODO mettre les type de charge et VH associé dans une table
                                'repeter_chaque_semaine': False
                            })

                        activite_soutenance.cible.clear()
                        activite_soutenance.cible.add(groupe_)
                        for enseignant in activite_soutenance.assuree_par.all():
                            activite_soutenance.assuree_par.remove(enseignant)
                        if soutenance_.president:
                            activite_soutenance.assuree_par.add(soutenance_.president)
                        if soutenance_.examinateur:
                            activite_soutenance.assuree_par.add(soutenance_.examinateur)
                        if soutenance_.rapporteur:
                            activite_soutenance.assuree_par.add(soutenance_.rapporteur)
                        if soutenance_.coencadrant:
                            activite_soutenance.assuree_par.add(soutenance_.coencadrant)
                        if soutenance_.assesseur1:
                            activite_soutenance.assuree_par.add(soutenance_.assesseur1)
                        if soutenance_.assesseur2:
                            activite_soutenance.assuree_par.add(soutenance_.assesseur2)

                        activite_soutenance.save()
                except Exception:
                    if settings.DEBUG:
                        raise Exception
                    else:
                        messages.error(request,
                                       "ERREUR: lors de l'enregistrement de l'évaluation du PFE. Merci de le signaler à l'administrateur.")
                        return render(request, 'scolar/note_pfe_update.html',
                                      {'form': form, 'liste_inscrits': liste_inscrits,
                                       'liste_evaluations': liste_evaluations, 'module': module_, 'groupe': groupe_})
                messages.success(request,
                                 "L'évaluation du PFE a bien été enregistrée. Vous pouvez passer signer le PV de délibération.")
                # redirect to a new URL:
            return HttpResponseRedirect(
                reverse('note_list', kwargs={'groupe_pk': groupe_pk, 'matiere_pk': module_.matiere.id}))
            # if a GET (or any other method) we'll create a blank form
    else:
        form = NotesPFEUpdateForm(groupe_pk, module_pk, request)
        messages.info(request,
                      "Utilisez ce formulaire pour introduire l'évaluation des différentes compétences attendues du PFE.")
    return render(request, 'scolar/note_pfe_update.html',
                  {'form': form, 'liste_inscrits': liste_inscrits, 'liste_evaluations': liste_evaluations,
                   'module': module_, 'groupe': groupe_})


@login_required
def note_pfe_lock(request, module_pk, groupe_pk):
    module_ = get_object_or_404(Module, id=module_pk)
    groupe_ = get_object_or_404(Groupe, id=groupe_pk)
    module_suivi_ = get_object_or_404(ModulesSuivis, groupe=groupe_, module=module_)

    if request.user.is_direction() or request.user.is_stage():
        pass
    else:
        messages.error(request, "Vous n'avez pas les permissions d'accès à cette opération")
        return redirect('/accounts/login/?next=%s' % request.path)
    try:
        if module_suivi_.saisie_notes == 'T':
            module_suivi_.saisie_notes = 'C'
        else:
            module_suivi_.saisie_notes = 'T'
        module_suivi_.save()
    except Exception:
        if settings.DEBUG:
            raise Exception
        else:
            messages.error(request, "ERREUR: lors du verrouillage / déverrouillage de saisie des notes.")
    else:
        messages.success(request, "Le verrouillage / déverrouillage a été réalisé avec succès!")
        # redirect to a new URL:
    return HttpResponseRedirect(reverse('notes_formation_detail', kwargs={'formation_pk': module_.formation.id,
                                                                          'periode_pk': module_.periode.id}))


class SeanceDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Seance
    permission_required = 'scolar.view_seance'

                                    #######################################Code Régit#################################################

def ChapitreCreate(request):
    if request.method == 'POST':
        chapitre = Chapitre(
            code_chap=request.POST['code_chap'],
            libelle_chap_FR=request.POST['libelle_chap_FR'],
            libelle_chap_AR=request.POST['libelle_chap_AR'],
        )
        chapitre.save()
        messages.success(request, 'Chapitre enregistré.')
    return render(request, 'scolar/add_chapitre.html')


def ChapitreShow(request):
    chapitre = Chapitre.objects.all()
    return render(request, 'scolar/show_chapitre.html', {'chapitre': chapitre})


def ChapitreDelete(request, id):
    chapitre = Chapitre.objects.get(id=id)
    delete = 1
    if request.method == "POST":
        chapitre.delete()
        messages.success(request, 'Chapitre supprimé.')
        return redirect('/scolar/ChapitreShow')
    return render(request, 'scolar/delete_item.html', {'delete': delete})


def ArticleCreate(request, art):
    pi = Chapitre.objects.get(pk=art)
    if request.method == 'POST':
        article = Article(
            chapitre=Chapitre.objects.get(pk=art),
            code_art=request.POST['code_art'],
            libelle_art_FR=request.POST['libelle_art_FR'],
            libelle_art_AR=request.POST['libelle_art_AR'],
        )
        article.save()
        messages.success(request, 'Article enregistré.')
        return redirect(request.path_info)
    else:
        # messages.error(request, "ERREUR: lors du verrouillage / déverrouillage de saisie des notes.")
        articles = Article.objects.filter(chapitre=Chapitre.objects.get(pk=art))
        # total_liste_soum = liste_soum.count()
        return render(request, 'scolar/add_article.html', {'articles': articles, 'pi': pi})


def ArticleDelete(request, art):
    article = Article.objects.get(pk=art)
    chapitre = article.chapitre_id
    delete = 2
    if request.method == "POST":
        article.delete()
        messages.success(request, 'Article supprimé.')
        return redirect('/scolar/ArticleCreate')
    return render(request, 'scolar/delete_item.html', {'delete': delete, 'chapitre': chapitre})


def CreditCreate(request):
    article = Article.objects.all()
    if request.method == 'POST':
        credit = Credit(
            chapitre_id=request.POST['chapitre'],
            article_id=request.POST['article'],
            credit_allouee=request.POST['credit_allouee'],
            credit_reste=request.POST['credit_allouee'],
        )
        credit.save()
        messages.success(request, 'credit enregistré.')
        return redirect(request.path_info)
    else:
        article = Article.objects.all()
        crdt = Credit.objects.all()
    return render(request, 'scolar/add_credit.html', {'article': article, 'crdt': crdt})


def CreditAssociate(request, art):
    pi = Article.objects.get(pk=art)
    article = Article.objects.all()
    if request.method == 'POST':
        credit = Credit(
            article=Article.objects.get(pk=art),
            chapitre=Chapitre.objects.get(pk=pi.chapitre_id),
            credit_allouee=request.POST['credit_allouee'],
            credit_reste=request.POST['credit_allouee'],
        )
        try:
            credit.save()
            messages.success(request, 'credit enregistré.')
            return redirect(request.path_info)
        except IntegrityError:

            messages.error(request, "Credit deja alloue pour cet Article_chapitre pour lexercice courrant")
            return redirect(request.path_info)
    credit_deja_alloue = Credit.objects.filter(article=pi).count()
    crdt = Credit.objects.all()
    if credit_deja_alloue > 0:
        messages.warning(request, 'Vous ne pouvez pas allouer un credit plusieurs fois a un article ')
        return render(request, 'scolar/add_credit.html', {'article': article, 'crdt': crdt})
    return render(request, 'scolar/ads_credit.html', {'pi': pi})


def CreditDelete(request, art):
    credit = Credit.objects.get(article=art)
    article = Article.objects.all()
    crdt = Credit.objects.all()
    delete = 3
    if request.method == "POST":
        credit.delete()
        messages.success(request, 'Credit supprimé.')
        return render(request, 'scolar/add_credit.html', {'article': article, 'crdt': crdt})
    return render(request, 'scolar/delete_item.html', {'delete': delete})


class aa_PDFView(PDFTemplateView):
    template_name = 'scolar/aa_pdf.html'
    cmd_options = {
        'orientation': 'Portrait',
        'page-size': 'A4',
    }
    def somme(self):
        chapitre = Chapitre.objects.get(pk=chap)
        articles = Article.objects.all()
        crdt = Credit.objects.all()
        somme = 0
        for crd in crdt:
            for article in articles:
                if chapitre == article.chapitre:
                    if article == crd.article:
                        somme = somme + crd.credit_allouee
                    else:
                        somme = somme
                else:
                    somme = somme
        return 5

    def get_context_data(self, **kwargs):
        articles = Article.objects.all()
        chapitres = Chapitre.objects.all()
        crdt = Credit.objects.all()
        vecteur = []
        for chapitre in chapitres:
            vecteur.append(chapitre)
            vecteur.append(Credit.objects.filter(chapitre=Chapitre.objects.get(pk=chapitre.id)).aggregate(Sum('credit_allouee')).get('credit_allouee__sum', 0.00))

        print('TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT')
        print(vecteur)
        print('TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT')


        #sum_pieces_letter = num2words(sum_pieces, lang='fr')

        context = {}
        context['year'] = datetime.datetime.now().year
        context['articles'] = articles
        context['chapitres'] = chapitres
        context['crdt'] = crdt
        context['vecteur'] = vecteur





        self.filename = 'Avance N° 01_' + str(datetime.datetime.now().year) + '.pdf'
        return context


def BordereauCreate(request, crdt):
    pi = Credit.objects.get(pk=crdt)
    ens = Regisseur.objects.get(user_id=request.user.id)
    print('=====================================================================================================')
    print(ens.prenom)
    #  print ( request.user.id)

    print('=====================================================================================================')
    if request.method == 'POST':
        borderau = Bordereau(
            credit=Credit.objects.get(pk=crdt),
            deseingnation=request.POST['deseingnation'],
            regisseur=ens,
        )
        borderau.save()
        messages.success(request, 'Borderzau enregistré avec succes.')
        return redirect(request.path_info)
    else:
        # messages.error(request, "ERREUR: lors du verrouillage / déverrouillage de saisie des notes.")
        borderaux = Bordereau.objects.filter(credit=Credit.objects.get(pk=crdt))
        # total_liste_soum = liste_soum.count()
        return render(request, 'scolar/add_bordereau.html', {'borderaux': borderaux})


def LitImput(request):
    credits = Credit.objects.all()
    return render(request, 'scolar/show_credit.html', {'credits': credits})



def PieceCreate(request, brdr):
    pi = Bordereau.objects.get(pk=brdr)
    credit = pi.credit
    print('44444444444444444444444444444444444444444444444444444444444')
    print(datetime.datetime.now().year)
    print('44444444444444444444444444444444444444444444444444444444444')
    if request.method == 'POST' and 'Enregistrer' in request.POST:
        piece = Piece(
            bordreau=Bordereau.objects.get(pk=brdr),
            credit=pi.credit,
            deseingnation=request.POST['deseingnation'],
            montant=request.POST['montant'],
        )
        credit_reste = pi.credit.credit_reste
        # credit.credit_reste.amount=credit.credit_reste.amount-piece.montant.amount
        if (credit.credit_reste.amount - piece.montant.amount) >= 0 and piece.montant.amount > 0:
            piece.save()
            credit.credit_reste.amount = credit.credit_reste.amount - piece.montant.amount
            credit.save(update_fields=['credit_reste'])
            messages.success(request, 'Piece justificatif ajoutéé  avec succes.')
            return redirect(request.path_info)
        else:
            messages.warning(request,
                             "Erreur: veuillez verifier le montant de la piece et aussi le credit reste pour cet article :  " + str(
                                 credit.credit_reste.amount) + "DZD")
            return redirect(request.path_info)

    if request.method == 'POST' and 'Cloturer' in request.POST:
        pi.cloture = 'True'
        pi.save(update_fields=['cloture'])
    pieces = Piece.objects.filter(bordreau=Bordereau.objects.get(pk=brdr))
    nb_pieces = Piece.objects.filter(bordreau=Bordereau.objects.get(pk=brdr)).count()
    print('___________________________________________________________________________________________')
    print (Piece.objects.filter(bordreau=pi).aggregate(Sum("montant")).get('montant__sum', 0.00))
    print('___________________________________________________________________________________________')
    if Piece.objects.filter(bordreau=pi).aggregate(Sum("montant")).get('montant__sum', 0.00) == None:
       sum_pieces=Money(0)
    else:
       sum_pieces = Money(Piece.objects.filter(bordreau=pi).aggregate(Sum("montant")).get('montant__sum', 0.00))





    return render(request, 'scolar/add_piece.html', {'pieces': pieces, 'nb_pieces': nb_pieces, 'sum_pieces': sum_pieces, 'pi': pi,
                   'year': datetime.datetime.now().year})


def PieceDelete(request, pc):
    piece = Piece.objects.get(pk=pc)
    pi = piece.bordreau
    # crdt = Credit.objects.all()
    delete = 4
    if request.method == "POST":
        pieces = Piece.objects.filter(bordreau=piece.bordreau)
        nb_pieces = Piece.objects.filter(bordreau=piece.bordreau).count()
        sum_pieces = Piece.objects.filter(bordreau=piece.bordreau).aggregate(Sum("montant")).get('montant__sum', 0.00)
        piece.delete()
        messages.success(request, 'piece supprimée avec succes')
        return redirect('PieceCreate', pi.id)
    return render(request, 'scolar/delete_item.html', {'delete': delete, 'pi': pi})


class aa_bordereau_PDFView(PDFTemplateView):
    template_name = 'scolar/aa_bordereau_pdf.html'
    cmd_options = {
        'orientation': 'Landscape',
        'page-size': 'A4',
    }

    def get_context_data(self, **kwargs):
        bordereau_ = Bordereau.objects.get(id=self.kwargs.get('bordereau_pk'))
        print('________________________________________________________')
        print(bordereau_.credit.credit_allouee)
        print('________________________________________________________')
        # self.filename='BordereauPDF.pdf'
        # pieces = Piece.objects.all()

        pieces = {}
        for piece_ in Piece.objects.filter(bordreau=bordereau_):
            print('88888888888888888888888888888888888888888888888888888888')
            print(piece_.credit.credit_allouee)
            print('88888888888888888888888888888888888888888888888888888888')
            pieces[piece_] = piece_

        sum_pieces = Piece.objects.filter(bordreau=bordereau_).aggregate(Sum("montant")).get('montant__sum', 0.00)
        nb_pieces = Piece.objects.filter(bordreau=bordereau_).count()
        sum_pieces_letter = num2words(sum_pieces, lang='fr')
        new_sum_pieces = Money(sum_pieces)

        context = {}
        context['year'] = datetime.datetime.now().year
        context['pieces'] = pieces
        context['bordereau'] = bordereau_
        context['sum_pieces'] = sum_pieces
        context['nb_pieces'] = nb_pieces
        context['sum_pieces_letter'] = sum_pieces_letter
        context['new_sum_pieces'] = new_sum_pieces

        print('ppppppppppppppppppppppppppppppppppppppppppppppppp')
        print(datetime.datetime.now().year)
        print(pieces)
        print(bordereau_)
        print(sum_pieces)

        self.filename = 'NumeroBordereau_' + str(datetime.datetime.now().year)  + '-' + str(bordereau_.id) + '.pdf'

        return context

